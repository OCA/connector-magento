# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import odoo
from datetime import datetime

from odoo.addons.component.core import Component
from odoo.addons.connector.unit.mapper import mapping
from odoo.addons.queue_job.job import identity_exact
from slugify import slugify
from odoo.addons.connector_magento.components.backend_adapter import MAGENTO_DATETIME_FORMAT


class ProductProductExporter(Component):
    _name = 'magento.product.product.exporter'
    _inherit = 'magento.exporter'
    _apply_on = ['magento.product.product']


    def _create_data(self, map_record, fields=None, **kwargs):
        # Here we do generate a new default code is none exists for now
        if not self.binding.default_code:
            name = self.binding.display_name
            for value in self.binding.attribute_value_ids:
                name = "%s %s %s" % (name, value.attribute_id.name, value.name)
            self.binding.default_code = slugify(name, to_lower=True)
        return super(ProductProductExporter, self)._create_data(map_record, fields=fields, **kwargs)

    def _create(self, data):
        """ Create the Magento record """
        # special check on data before export
        res = super(ProductProductExporter, self)._create(data)
        self.binding.with_context(
            no_connector_export=True).magento_id = data['id']
        return res

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
        for attr in data.get('custom_attributes', []):
            data[attr['attribute_code']] = attr['value']
        # Do use the importer to update the binding
        importer = self.component(usage='record.importer',
                                model_name='magento.product.product')
        importer.run(data, force=True, binding=self.binding)
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
            self.binding.with_delay(identity_key=identity_exact).import_record(self.backend_record,
                                                self.external_id,
                                                force=True)

    def _export_dependencies(self):
        """ Export the dependencies for the record"""
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
        return

    def _after_export(self):
        def sort_by_position(elem):
            return elem.position

        # We do export the base image on position 0
        mbinding = None
        for media_binding in sorted(self.binding.magento_image_bind_ids.filtered(lambda m: m.media_type == 'image'), key=sort_by_position):
            mbinding = media_binding
            break
        if not mbinding:
            # Create new media binding entry for main image
            mbinding = self.env['magento.product.media'].with_context(connector_no_export=True).create({
                'backend_id': self.binding.backend_id.id,
                'magento_product_id': self.binding.id,
                'label': self.binding.odoo_id.name,
                'file': "%s.png" % slugify(self.binding.odoo_id.name).lower(),
                'position': 1,
                'mimetype': 'image/png',
            })
        self._export_dependency(mbinding, "magento.product.media")


class ProductProductExportMapper(Component):
    _name = 'magento.product.export.mapper'
    _inherit = 'magento.export.mapper'
    _apply_on = ['magento.product.product']

    direct = [
        ('default_code', 'sku'),
        ('product_type', 'typeId'),
    ]

    @mapping
    def names(self, record):
        storeview_id = self.work.storeview_id if hasattr(self.work, 'storeview_id') else False
        name = record.name
        if storeview_id:
            value_ids = record.\
            magento_attribute_line_ids.filtered(
                lambda att:
                    att.odoo_field_name.name == 'name'
                    and att.store_view_id == storeview_id
                    and att.attribute_id.create_variant != True
                    and (
                        att.attribute_text != False
                    )
                )
            name = value_ids[0].attribute_text
        return {'name': name}

    @mapping
    def visibility(self, record):
        return {'visibility': record.visibility}

    @mapping
    def status(self, record):
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
            data.update(self.category_ids(record))
        return {'extension_attributes': data}
    
    
    def get_website_ids(self, record):
        website_ids = [
                s.external_id for s in record.backend_id.website_ids
                ]
        return {'website_ids': website_ids}
    
    def category_ids(self, record):
        magento_categ_id = record.categ_id.magento_bind_ids.filtered(
            lambda bc: bc.backend_id.id == record.backend_id.id)
        categ_vals = [
            {
              "position": 0,
              "category_id": magento_categ_id.external_id,
          }
        ]
        i = 1
        for c in record.categ_ids:
            for b in c.magento_bind_ids.filtered(lambda bc: bc.backend_id.id == record.backend_id.id):
                categ_vals.append({
                    "position": i,
                    "category_id": b.external_id,
                })
                i += 1
        return {'category_links': categ_vals}
    
    
    @mapping
    def get_associated_configurable_product_id(self, record):
        return {}
    
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
    def get_common_attributes(self, record):
        """
        Collect attributes to prensent it regarding to
        https://devdocs.magento.com/swagger/index_20.html
        catalogProductRepositoryV1 / POST 
        """

        customAttributes = []
        storeview_id = self.work.storeview_id if hasattr(self.work, 'storeview_id') else False
        magento_attribute_line_ids = record.magento_attribute_line_ids.filtered(
            lambda att: att.store_view_id.id==storeview_id and (
                        att.attribute_text or att.attribute_select.id or len(att.attribute_multiselect.ids) > 0))

        for values_id in magento_attribute_line_ids:
            """ Deal with Custom Attributes """            
            attributeCode = values_id.attribute_id.attribute_code
            if attributeCode == 'category_ids':
                # Ignore category here - will get set using the category_links
                continue
            value = values_id.attribute_text
            if values_id.magento_attribute_type == 'boolean':
                try:
                    value = int(values_id.attribute_text)
                except:
                    value = 0
            
            if values_id.magento_attribute_type in ['select',] and \
                    values_id.attribute_select.external_id != False:
                full_value = values_id.attribute_select.external_id
                value = full_value.split('_')[1]
            
            customAttributes.append({
                'attribute_code': attributeCode,
                'value': value
                })     
        
        for values_id in record.attribute_value_ids:
            """ Deal with Attributes in the 'variant' part of Odoo"""
            odoo_value_ids = values_id.magento_bind_ids.filtered(
                lambda m: m.backend_id == record.backend_id)
            for odoo_value_id in odoo_value_ids:
                attributeCode = odoo_value_id.magento_attribute_id.attribute_code
                value = odoo_value_id.external_id.split('_')[1]
                customAttributes.append({
                    'attributeCode': attributeCode,
                    'value': value
                    })
        result = {'custom_attributes': customAttributes}
        return result

    @mapping
    def price(self, record):
        price = record['lst_price']
        return {'price': price}
