# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import odoo
from datetime import datetime

from odoo.addons.component.core import Component
from odoo.addons.connector.unit.mapper import mapping
from slugify import slugify
from odoo.addons.connector_magento.components.backend_adapter import MAGENTO_DATETIME_FORMAT
import magic
import base64
import logging

_logger = logging.getLogger(__name__)


class ProductProductExporter(Component):
    _name = 'magento.product.product.exporter'
    _inherit = 'magento.exporter'
    _apply_on = ['magento.product.product']

    def _sku_inuse(self, sku):
        search_count = self.env['magento.product.template'].search_count([
            ('backend_id', '=', self.backend_record.id),
            ('external_id', '=', sku),
        ])
        if not search_count:
            search_count += self.env['magento.product.product'].search_count([
                ('backend_id', '=', self.backend_record.id),
                ('external_id', '=', sku),
            ])
        if not search_count:
            search_count += self.env['magento.product.bundle'].search_count([
                ('backend_id', '=', self.backend_record.id),
                ('external_id', '=', sku),
            ])
        return search_count > 0

    def _get_sku_proposal(self):
        def sort_by_sequence(elem):
            return elem.attribute_id.sequence

        if self.binding.default_code:
            sku = self.binding.default_code[0:64]
        else:
            name = self.binding.display_name
            for value in sorted(self.binding.attribute_value_ids, key=sort_by_sequence):
                # Check the attribute for the product template - it should have more than one value to be useful here
                line = self.binding.odoo_id.product_tmpl_id.attribute_line_ids.filtered(
                    lambda l: l.attribute_id == value.attribute_id)
                if len(line.value_ids) > 1:
                    name = "%s %s %s" % (name, value.attribute_id.name, value.name)
            sku = slugify(name, to_lower=True)[0:64]
        return sku

    def _create_data(self, map_record, fields=None, **kwargs):
        # Here we do generate a new default code is none exists for now
        if 'magento.product.product' in self._apply_on and not self.binding.external_id:
            sku = self._get_sku_proposal()
            i = 0
            original_sku = sku
            while self._sku_inuse(sku):
                sku = "%s-%s" % (original_sku[0:(63-len(str(i)))], i)
                i += 1
                _logger.info("Try next sku: %s", sku)
            self.binding.with_context(connector_no_export=True).external_id = sku
            # TODO: Add backend option to enable / disable this !
            '''
            if not self.binding.default_code:
                self.binding.with_context(connector_no_export=True).default_code = sku
            '''
        return super(ProductProductExporter, self)._create_data(map_record, fields=fields, **kwargs)

    def _create(self, data):
        """ Create the Magento record """
        # special check on data before export
        res = super(ProductProductExporter, self)._create(data)
        self.binding.with_context(
            no_connector_export=True).magento_id = data['id']
        return res

    def _update(self, data):
        """ Create the Magento record """
        # special check on data before export
        return super(ProductProductExporter, self)._update(data)

    def _should_import(self):
        """ Before the export, compare the update date
        in Magento and the last sync date in Odoo,
        Regarding the product_synchro_strategy Choose 
        to whether the import or the export is necessary
        """
        assert self.binding
        if not self.external_id:
            return False
        if self.backend_record.product_synchro_strategy == 'odoo_first':
            return False
        sync = self.binding.sync_date
        if not sync:
            return True
        record = self.backend_adapter.read(self.external_id,
                                           attributes=['updated_at'])
        if not record['updated_at']:
            # in rare case it can be empty, in doubt, import it
            return True
        sync_date = odoo.fields.Datetime.from_string(sync)
        magento_date = datetime.strptime(record['updated_at'],
                                         MAGENTO_DATETIME_FORMAT)
        return sync_date < magento_date

    def _update_binding_record_after_create(self, data):
        """
        This will only get called on a new product export - not on updates !
        :param data:
        :return:
        """
        for attr in data.get('custom_attributes', []):
            data[attr['attribute_code']] = attr['value']
        # Do use the importer to update the binding
        importer = self.component(usage='record.importer',
                                model_name='magento.product.product')
        _logger.info("Do update record with: %s", data)
        importer.run(data, force=True, binding=self.binding.sudo())
        self.external_id = data['sku']

    def _delay_import(self):
        """ Schedule an import/export of the record.

        Adapt in the sub-classes when the model is not imported
        using ``import_record``.
        """
        # force is True because the sync_date will be more recent
        # so the import would be skipped
        assert self.external_id
        if self.backend_record.product_synchro_strategy == 'magento_first':
            self.binding.import_record(self.backend_record, self.external_id, force=True)

    def _export_categories(self):
        # Check for categories
        magento_categ_id = self.binding.categ_id.magento_bind_ids.filtered(lambda bc: bc.backend_id.id == self.backend_record.id)
        if not magento_categ_id:
            # We need to export the category first
            self._export_dependency(self.binding.categ_id, "magento.product.category")
        for extra_category in self.binding.categ_ids:
            magento_categ_id = extra_category.magento_bind_ids.filtered(lambda bc: bc.backend_id.id == self.backend_record.id)
            if not magento_categ_id:
                # We need to export the category first
                self._export_dependency(extra_category, "magento.product.category")

    def _export_attribute_values(self):
        # Then the attribute values
        record = self.binding
        att_exporter = self.component(usage='record.exporter', model_name='magento.product.attribute')
        exported_attribute_ids = []
        for att_line in record.attribute_line_ids:
            m_att_id = att_line.attribute_id.magento_bind_ids.filtered(lambda m: m.backend_id == self.backend_record)
            if not m_att_id and att_line.attribute_id.id not in exported_attribute_ids:
                # We need to export the attribute first
                self._export_dependency(att_line.attribute_id, "magento.product.attribute", binding_extra_vals={
                    'create_variant': True,
                })
                m_att_id = att_line.attribute_id.magento_bind_ids.filtered(
                    lambda m: m.backend_id == self.backend_record)
                exported_attribute_ids.append(att_line.attribute_id.id)
            m_att_values = []
            needs_sync = False
            for value_id in att_line.value_ids:
                m_value_id = value_id.magento_bind_ids.filtered(lambda m: m.backend_id == self.backend_record)
                if not m_value_id:
                    m_att_values.append((0, 0, {
                        'attribute_id': att_line.attribute_id.id,
                        'magento_attribute_id': m_att_id.id,
                        'odoo_id': value_id.id,
                        'backend_id': self.backend_record.id,
                    }))
                    needs_sync = True
                else:
                    m_att_values.append((4, m_value_id.id))
            if needs_sync:
                # Write the values - then update the attribute
                m_att_id.sudo().with_context(connector_no_export=True).magento_attribute_value_ids = m_att_values
                # We only do sync if a new attribute arrived
                att_exporter.run(m_att_id)

    def _export_dependencies(self):
        """ Export the dependencies for the record"""
        self._export_categories()
        self._export_attribute_values()
        # Clear spezial prices here
        if self.binding.external_id:
            self.backend_adapter.remove_special_price(self.binding.external_id)
            if self.binding.special_price_active:
                self.binding.with_context(connector_no_export=True).special_price_active = False
        return

    def _export_base_image(self):
        def sort_by_position(elem):
            return elem.position

        # We do export the base image on position 0
        mbinding = None
        for media_binding in sorted(self.binding.magento_image_bind_ids.filtered(lambda m: m.type == 'product_image'), key=sort_by_position):
            mbinding = media_binding
            break
        # Create new media binding entry for main image
        mime = magic.Magic(mime=True)
        mimetype = mime.from_buffer(base64.b64decode(self.binding.odoo_id.image))
        extension = 'png' if mimetype == 'image/png' else 'jpeg'
        if 'magento.product.template' in self._apply_on:
            model_key = 'magento_product_tmpl_id'
        else:
            model_key = 'magento_product_id'
        # Find unique filename
        filename = "%s.%s" % (slugify(self.binding.odoo_id.name, to_lower=True), extension)
        i = 0
        while self.env['magento.product.media'].search_count([
            ('backend_id', '=', self.binding.backend_id.id),
            ('file', '=', filename)
        ]) > 0:
            filename = "%s-%s.%s" % (slugify(self.binding.odoo_id.name, to_lower=True), i, extension)
            i += 1
        if not mbinding:
            mbinding = self.env['magento.product.media'].sudo().with_context(connector_no_export=True).create({
                'backend_id': self.binding.backend_id.id,
                model_key: self.binding.id,
                'label': self.binding.odoo_id.name,
                'file': filename,
                'type': 'product_image',
                'position': 1,
                'mimetype': mimetype,
                'image_type_image': True,
                'image_type_small_image': True,
                'image_type_thumbnail': True,
            })
        else:
            mbinding.sudo().with_context(connector_no_export=True).update({
                'label': self.binding.odoo_id.name,
                'file': filename,
                'mimetype': mimetype,
                'image_type_image': True,
                'image_type_small_image': True,
                'image_type_thumbnail': True,
            })
        self._export_dependency(mbinding.sudo(), "magento.product.media", force_update=True)

    def _export_stock(self):
        for stock_item in self.binding.magento_stock_item_ids:
            stock_item.sync_to_magento()

    def _after_export(self):
        self._export_base_image()
        self._export_stock()


class ProductProductExportMapper(Component):
    _name = 'magento.product.export.mapper'
    _inherit = 'magento.export.mapper'
    _apply_on = ['magento.product.product']

    direct = [
        ('external_id', 'sku'),
        ('product_type', 'typeId'),
    ]

    @mapping
    def names(self, record):
        return {'name': record.name}

    @mapping
    def visibility(self, record):
        return {'visibility': record.visibility}

    @mapping
    def status(self, record):
        _logger.info("In original status mapping function")
        return {'status': 1 if record.active else 0}

    @mapping
    def get_type(self, record):
        return {'typeId': 'simple'}

    @mapping
    def get_extension_attributes(self, record):
        data = {}
        storeview_id = self.work.storeview_id if hasattr(self.work, 'storeview_id') else False
        if not storeview_id:
            data.update(self.get_website_ids(record))
            #data.update(self.category_ids(record))
        return {'extension_attributes': data}
    
    def get_website_ids(self, record):
        website_ids = [s.external_id for s in record.backend_id.website_ids]
        return {'website_ids': website_ids}
    
    '''
    def category_ids(self, record):
        magento_categ_id = record.categ_id.magento_bind_ids.filtered(lambda bc: bc.backend_id.id == record.backend_id.id)
        categ_vals = [{
            "position": 0,
            "category_id": magento_categ_id.external_id,
        }]
        i = 1
        for c in record.categ_ids:
            for b in c.magento_bind_ids.filtered(lambda bc: bc.backend_id.id == record.backend_id.id):
                categ_vals.append({
                    "position": i,
                    "category_id": b.external_id,
                })
                i += 1
        return {'category_links': categ_vals}
    '''

    def category_ids(self, record):
        magento_categ_id = record.categ_id.magento_bind_ids.filtered(lambda bc: bc.backend_id.id == record.backend_id.id)
        c_ids = []
        c_ids.append(magento_categ_id.external_id)
        for c in record.categ_ids:
            for b in c.magento_bind_ids.filtered(lambda bc: bc.backend_id.id == record.backend_id.id):
                c_ids.append(b.external_id)
        return {
            'attribute_code': 'category_ids',
            'value': c_ids
        }

    @mapping
    def weight(self, record):
        if record.weight:
            val = record.weight
        else:
            val = 0        
        return {'weight': val}
        
    @mapping
    def attribute_set_id(self, record):
        if record.attribute_set_id:
            val = record.attribute_set_id.external_id
        else:
            val = record.backend_id.default_attribute_set_id.external_id
        return {'attributeSetId': val}

    @mapping
    def get_custom_attributes(self, record):
        custom_attributes = []
        for values_id in record.attribute_value_ids:
            """ Deal with Attributes in the 'variant' part of Odoo"""
            odoo_value_ids = values_id.magento_bind_ids.filtered(
                lambda m: m.backend_id == record.backend_id)
            for odoo_value_id in odoo_value_ids:
                attributeCode = odoo_value_id.magento_attribute_id.attribute_code
                value = odoo_value_id.external_id.split('_')[1]
                custom_attributes.append({
                    'attributeCode': attributeCode,
                    'value': value
                })
        if record.backend_id.default_pricelist_id.discount_policy == 'without_discount' and record.with_context(
                pricelist=record.backend_id.default_pricelist_id.id).price != record['lst_price']:
            custom_attributes.append({
                'attributeCode': 'special_price',
                'value': record.with_context(pricelist=record.backend_id.default_pricelist_id.id).price
            })
            record.with_context(connector_no_export=True).special_price_active = True
        custom_attributes.append(self.category_ids(record))
        _logger.info("Do use custom attributes: %r", custom_attributes)
        return {'custom_attributes': custom_attributes}

    @mapping
    def price(self, record):
        if record.backend_id.default_pricelist_id.discount_policy=='with_discount':
            price = record.with_context(pricelist=record.backend_id.default_pricelist_id.id).price
        else:
            price = record['lst_price']
        return {
            'price': price,
        }
