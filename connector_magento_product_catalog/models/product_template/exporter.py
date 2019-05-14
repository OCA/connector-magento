# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


import odoo
from datetime import datetime

from odoo.addons.component.core import Component
from odoo.addons.connector.unit.mapper import mapping, only_create
from odoo.addons.queue_job.job import identity_exact
from odoo.addons.connector.exception import MappingError
from slugify import slugify

from odoo.addons.connector_magento.components.backend_adapter import MAGENTO_DATETIME_FORMAT


class ProductTemplateDefinitionExporter(Component):
    _name = 'magento.product.template.exporter'
    _inherit = 'magento.exporter'
    _apply_on = ['magento.product.template']

    def _create_data(self, map_record, fields=None, **kwargs):
        # Here we do generate a new default code is none exists for now
        if not self.binding.external_id:
            sku = slugify(self.binding.display_name, to_lower=True)
            search_count = self.env['magento.product.template'].search_count([
                ('backend_id', '=', self.backend_record.id),
                ('external_id', '=', sku),
            ])
            if search_count > 0:
                sku = slugify("%s-%s" % (self.binding.display_name, self.binding.id), to_lower=True)
            self.binding.external_id = sku
        return super(ProductTemplateDefinitionExporter, self)._create_data(map_record, fields=fields, **kwargs)

    def _create(self, data):
        """ Create the Magento record """
        # special check on data before export
        res = super(ProductTemplateDefinitionExporter, self)._create(data)
        self.binding.magento_id = data['id']
        return res

    def _export_dependencies(self):
        """ Export the dependencies for the record"""
        record = self.binding
        # First - do export the attributes needed
        att_lines = record.attribute_line_ids.filtered(lambda l: l.attribute_id.create_variant == True)
        exported_attribute_ids = []
        for att_line in att_lines:
            m_att_id = att_line.attribute_id.magento_bind_ids.filtered(lambda m: m.backend_id == self.backend_record)
            if not m_att_id and att_line.attribute_id.id not in exported_attribute_ids:
                # We need to export the attribute first
                self._export_dependency(att_line.attribute_id, "magento.product.attribute", binding_extra_vals={
                    'create_variant': True,
                })
        # Then the attribute values
        att_exporter = self.component(usage='record.exporter', model_name='magento.product.attribute')
        for att_line in att_lines:
            m_att_id = att_line.attribute_id.magento_bind_ids.filtered(lambda m: m.backend_id == self.backend_record)
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
            # Write the values - then update the attribute
            m_att_id.with_context(connector_no_export=True).magento_attribute_value_ids = m_att_values
            if needs_sync:
                # We only do sync if a new attribute arrived
                att_exporter.run(m_att_id)

        variant_exporter = self.component(usage='record.exporter', model_name='magento.product.product')
        for p in record.product_variant_ids:
            m_prod = p.magento_bind_ids.filtered(lambda m: m.backend_id == record.backend_id)
            if not m_prod.id:
                m_prod = self.env['magento.product.product'].with_context(connector_no_export=True).create({
                    'backend_id': self.backend_record.id,
                    'odoo_id': p.id,
                    'attribute_set_id': record.attribute_set_id.id,
                    'magento_configurable_id': record.id,
                    'visibility': '1',
                })
                variant_exporter.run(m_prod)

    def _after_export(self):
        storeview_id = self.work.storeview_id if hasattr(self.work, 'storeview_id') else False
        if storeview_id:
            # We are already in the storeview specific export
            return
        # TODO Fix and enable again
        '''
        for storeview_id in self.env['magento.storeview'].search([('backend_id', '=', self.backend_record.id)]):
            self.binding.with_delay().export_product_template_for_storeview(storeview_id=storeview_id)
        '''

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

    
    def _delay_import(self):
        """ Schedule an import/export of the record.

        Adapt in the sub-classes when the model is not imported
        using ``import_record``.
        """
        # force is True because the sync_date will be more recent
        # so the import would be skipped
        assert self.external_id
        if self.backend_record.product_synchro_strategy == 'magento_first':
            self.binding.with_delay(
                identity_key=identity_exact).import_record(self.backend_record,
                                                self.external_id,
                                                force=True)


class ProductTemplateExportMapper(Component):
    _name = 'magento.product.template.export.mapper'
    _inherit = 'magento.export.mapper'
    _apply_on = ['magento.product.template']
    
    direct = []
    
    @mapping
    def names(self, record):
        return {'name': record.name}
    
    @mapping
    def visibility(self, record):
        return {'visibility': 4}
    
    
    @mapping
    def product_type(self, record):
        product_type = 'simple'
        if record.product_variant_count > 1:
            product_type = 'configurable'
        return {'typeId': product_type}
    
    @mapping
    def default_code(self, record):
        return {'sku': record.external_id}
    
    @mapping
    def price(self, record):
        price = record['lst_price']
        return {'price': price}
      
    
    @mapping
    def get_extension_attributes(self, record):
        data = {}
        storeview_id = self.work.storeview_id if hasattr(self.work, 'storeview_id') else False
        if not storeview_id:
            return {}
        data.update(self.get_website_ids(record))
        data.update(self.category_ids(record))
        data.update(self.configurable_product_options(record))
        data.update(self.configurable_product_links(record))
        return {'extension_attributes': data}


    def configurable_product_links(self, record):
        links = []
        for p in record.product_variant_ids:
            mp = p.magento_bind_ids.filtered(
                lambda m: m.backend_id == record.backend_id)
            if not mp.external_id:
                continue
            links.append(mp.magento_id)
        return {'configurable_product_links': links}


    def configurable_product_options(self, record):
        option_ids = []
        att_lines = record.attribute_line_ids.filtered(lambda l: l.attribute_id.create_variant == True and len(l.attribute_id.magento_bind_ids.filtered(lambda m: m.backend_id == record.backend_id)) > 0)
        for l in att_lines:
            m_att_id = l.attribute_id.magento_bind_ids.filtered(lambda m: m.backend_id == record.backend_id)
            if not m_att_id:
                raise MappingError("The product attribute %s "
                                   "is not exported yet." %
                                   l.attribute_id.name)
            if not m_att_id.is_pivot_attribute:
                continue
            opt = {
                "id": 1,
                "attribute_id": m_att_id.external_id,
                "label": m_att_id.attribute_code,
                "position": 0,
                "values": []
            }
            for v in l.value_ids:
                v_ids = v.magento_bind_ids.filtered(lambda m: m.backend_id == record.backend_id)
                for v_id in v_ids: 
                    opt['values'].append({ "value_index": v_id.external_id.split('_')[1]})
                
            option_ids.append(opt)
        return {'configurable_product_options': option_ids}

    def get_website_ids(self, record):
        website_ids = [
                s.external_id for s in record.backend_id.website_ids
                ]
        return {'website_ids': website_ids}

    def category_ids(self, record):
        categ_vals = [{
            "position": 0,
            "category_id": record.categ_id.magento_bind_ids.external_id,
        }]
        for c in record.categ_ids:
            categ_vals.append({
                "position": 1,
                "category_id": c.magento_bind_ids.external_id,
            })
        return {'category_links': categ_vals}

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
