# -*- coding: utf-8 -*-
# Copyright 2018 akretion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import Component

from odoo.addons.connector.components.mapper import mapping
from odoo.addons.connector.exception import MappingError
from odoo.addons.connector_magento.components.mapper import normalize_datetime


class TemplateBatchImporter(Component):
    """ Import the Magento Configurables.

    creates a job for every product where 'type' = 'configurable'
    """
    _name = 'magento.product.template.batch.importer'
    _inherit = 'magento.product.product.batch.importer'
    _apply_on = ['magento.product.template']


class TemplateImportMapper(Component):
    _name = 'magento.product.template.import.mapper'
    _inherit = 'magento.product.product.import.mapper'
    _apply_on = ['magento.product.template']

    direct = [('name', 'name'),
              ('description', 'description'),
              ('weight', 'weight'),
              ('cost', 'standard_price'),
              ('short_description', 'description_sale'),
              ('sku', 'default_code'),
              (normalize_datetime('created_at'), 'created_at'),
              (normalize_datetime('updated_at'), 'updated_at'),
              ]

    @mapping
    def variant_managed_by_magento(self, record):
        return {'variant_managed_by_magento': True}


class TemplateImporter(Component):
    _name = 'magento.product.template.importer'
    _inherit = 'magento.importer'
    _apply_on = ['magento.product.template']

    def _import_dependencies(self):
        record = self.magento_record
        # import related categories
        for mag_category_id in record['categories']:
            self._import_dependency(mag_category_id,
                                    'magento.product.category')

    def _prepare_attribute_vals(self, attribute):
        attr_binder = self.binder_for('magento.product.attribute')
        attr = attr_binder.to_internal(attribute['attribute_id'], unwrap=True)

        val_binder = self.binder_for('magento.product.attribute.value')
        attribute_vals = []
        for magento_value in attribute['values']:
            value = val_binder.to_internal(
                magento_value['value_index'], unwrap=True)
            if value:
                attribute_vals.append(value.id)
        return {'attribute_id': attr.id, 'value_ids': [(6, 0, attribute_vals)]}

    def _prepare_attr_lines(self, binding, magento_attributes):
        attribute_line_vals = []
        for attribute in magento_attributes:
            vals = self._prepare_attribute_vals(attribute)
            line = self.env['product.attribute.line'].search([
                ('attribute_id', '=', vals['attribute_id']),
                ('product_tmpl_id', '=', binding.odoo_id.id)
            ])
            if line:
                attribute_line_vals.append((1, line.id, vals))
            else:
                attribute_line_vals.append((0, 0, vals))

    def _after_import(self, binding):
        sku = self.magento_record['sku']
        attrs = self.backend_adapter.list_attributes(sku)

        attr_importer = self.component(
            usage='record.importer',
            model_name='magento.product.attribute')

        for attribute in attrs:
            attr_importer.run(attribute)
  
        binding.write(
            {'attribute_line_ids': self._prepare_attr_lines(binding, attrs)})

        value_binder = self.binder_for('magento.product.attribute.value')
        product_binder = self.binder_for('magento.product.product')

        variants = self.backend_adapter.list_variants(sku)
        for variant in variants:
            attribute_value_ids = []
            self._import_dependency(
                variant['entity_id'], 'magento.product.product')
            product = product_binder.to_internal(
                variant['entity_id'], unwrap=True)
            for attribute in attrs:
                if variant.get(attribute['attribute_code']):
                    value = value_binder.to_internal(
                        variant[attribute['attribute_code']],
                        unwrap=True)
                    if not value:
                        raise MappingError(
                            "The attribute value with "
                            "magento id %s is not imported." %
                            variant[attribute['attribute_code']])
                    attribute_value_ids.append(value.id)
            vals = {'attribute_value_ids': [(6, 0, attribute_value_ids)]}
            template = product.product_tmpl_id
            if template != binding.odoo_id:
                vals['product_tmpl_id'] = binding.odoo_id.id
            product.write(vals)
            if not template.product_variant_ids:
                template.unlink()
            else:
                if template != binding.odoo_id:
                    raise MappingError(
                        "The template for the product %s (sku %s)"
                        " has many variants" % product.id, variant['sku'])
