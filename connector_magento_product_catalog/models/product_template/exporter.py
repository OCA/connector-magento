# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# Copyright 2019 Callino
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


from odoo.addons.component.core import Component
from odoo.addons.connector.unit.mapper import mapping, only_create
from odoo.addons.connector.exception import MappingError
from slugify import slugify
import logging

_logger = logging.getLogger(__name__)


class ProductTemplateDefinitionExporter(Component):
    _name = 'magento.product.template.exporter'
    _inherit = 'magento.product.product.exporter'
    _apply_on = ['magento.product.template']

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
        if self.binding.magento_default_code:
            sku = self.binding.magento_default_code[0:64]
        else:
            sku = slugify(self.binding.display_name, to_lower=True)[0:64]
        return sku

    def _create_data(self, map_record, fields=None, **kwargs):
        # Here we do generate a new default code is none exists for now
        if not self.binding.external_id:
            sku = self._get_sku_proposal()
            i = 0
            original_sku = sku
            while self._sku_inuse(sku):
                sku = "%s-%s" % (original_sku[0:(63-len(str(i)))], i)
                i += 1
                _logger.info("Try next sku: %s", sku)
            self.binding.with_context(connector_no_export=True).external_id = sku
        return super(ProductTemplateDefinitionExporter, self)._create_data(map_record, fields=fields, **kwargs)

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
                                model_name='magento.product.template')
        _logger.info("Do update record with: %s", data)
        importer.run(data, force=True, binding=self.binding)
        self.external_id = data['sku']

    def _export_variants(self):
        record = self.binding
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

    def _create_attribute_lines(self):
        record = self.binding
        for line in record.attribute_line_ids:
            m_line = line.magento_bind_ids.filtered(lambda m: m.backend_id == record.backend_id)
            m_att_id = line.attribute_id.magento_bind_ids.filtered(lambda m: m.backend_id == record.backend_id)
            if not m_att_id:
                raise MappingError("The product attribute %s "
                                   "is not exported yet." %
                                   line.attribute_id.name)

            if not m_line:
                self.env['magento.template.attribute.line'].sudo().create({
                    'odoo_id': line.id,
                    'magento_attribute_id': m_att_id.id,
                    'magento_template_id': record.id,
                    'label': m_att_id.name,
                    'position': m_att_id.sequence,
                })

    def _export_dependencies(self):
        """ Export the dependencies for the record"""
        super(ProductTemplateDefinitionExporter, self)._export_dependencies()
        self._create_attribute_lines()
        self._export_variants()
        return

    def _after_export(self):
        super(ProductTemplateDefinitionExporter, self)._after_export()
        storeview_id = self.work.storeview_id if hasattr(self.work, 'storeview_id') else False
        if storeview_id:
            # We are already in the storeview specific export
            return
        # TODO Fix and enable again
        '''
        for storeview_id in self.env['magento.storeview'].search([('backend_id', '=', self.backend_record.id)]):
            self.binding.export_product_template_for_storeview(storeview_id=storeview_id)
        '''


class ProductTemplateExportMapper(Component):
    _name = 'magento.product.template.export.mapper'
    _inherit = 'magento.export.mapper'
    _apply_on = ['magento.product.template']
    
    direct = []
    
    @mapping
    def names(self, record):
        storeview_id = self.work.storeview_id or False
        name = record.name
        if storeview_id:
            value_ids = record.\
            magento_template_attribute_value_ids.filtered(
                lambda att: 
                    att.odoo_field_name.name == 'name'
                    and att.store_view_id.id == storeview_id.id
                    and att.attribute_id.create_variant != True
                    and (
                        att.attribute_text != False
                    )
                )
        if len(value_ids) == 0:
            _logger.debug("No name found for %s on storeview %s" % (name, storeview_id))
        else:
            name = value_ids[0].attribute_text
        return {'name': name}

    
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
        if record.backend_id.default_pricelist_id.discount_policy=='with_discount':
            price = record.with_context(pricelist=record.backend_id.default_pricelist_id.id).price
        else:
            price = record['list_price']
        return {'price': price}

    @mapping
    def get_extension_attributes(self, record):
        data = {}
        data.update(self.get_website_ids(record))
        #data.update(self.category_ids(record))
        data.update(self.configurable_product_options(record))
        data.update(self.configurable_product_links(record))
        return {'extension_attributes': data}


    def configurable_product_links(self, record):
        links = []
        for p in record.product_variant_ids:
            mp = p.magento_bind_ids.filtered(lambda m: m.backend_id == record.backend_id)
            if not mp.external_id:
                continue
            links.append(mp.magento_id)
        return {'configurable_product_links': links}

    def configurable_product_options(self, record):
        option_ids = []
        att_lines = record.attribute_line_ids.filtered(lambda l: l.attribute_id.create_variant == True and len(l.attribute_id.magento_bind_ids.filtered(lambda m: m.backend_id == record.backend_id)) > 0)
        for l in att_lines:
            if not l.value_ids or len(l.value_ids) < 2:
                # Do not export attributes with only one selectable value !
                continue
            m_att_id = l.attribute_id.magento_bind_ids.filtered(lambda m: m.backend_id == record.backend_id)
            if not m_att_id:
                raise MappingError("The product attribute %s "
                                   "is not exported yet." %
                                   l.attribute_id.name)
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
                s.external_id for s in record.website_ids
                ]
        return {'website_ids': website_ids}

    def category_ids(self, record):
        c_ids = []
        c_ids.append(record.categ_id.magento_bind_ids.filtered(lambda m: m.backend_id == record.backend_id).external_id)
        for c in record.categ_ids:
            c_ids.append(c.magento_bind_ids.filtered(lambda m: m.backend_id == record.backend_id).external_id)
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
        custom_attributes.append(self.category_ids(record))
        if record.magento_url_key:
            custom_attributes.append({
                'attribute_code': 'url_key',
                'value': record.magento_url_key
            })
        result = {'custom_attributes': custom_attributes}
        return result

    @mapping
    def status(self, record):
        return {'status': '2' if not record.active else record.magento_status}

    @mapping
    def option_products(self, record):
        return {}


    @mapping
    def crossproducts(self, record):
        return {}
