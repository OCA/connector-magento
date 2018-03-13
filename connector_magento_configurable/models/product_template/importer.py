# -*- coding: utf-8 -*-
# Copyright 2018 akretion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import _
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

    direct = [
        ('name', 'name'),
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


class CatalogImageImporter(Component):
    _inherit = 'magento.product.image.importer'
    _apply_on = ['magento.product.product', 'magento.product.template']


class TemplateImporter(Component):
    _name = 'magento.product.template.importer'
    _inherit = 'magento.product.product.importer'
    _apply_on = ['magento.product.template']

    def _must_skip(self):
        if self.magento_record['type_id'] != 'configurable':
            return _('The template must be imported from a configurable.')

    def _validate_product_type(self, data):
        return

    def _prepare_attribute_vals(self, attribute):
        val_binder = self.binder_for('magento.product.attribute.value')
        attribute_values = self.env['product.attribute.value'].browse(False)
        for magento_value in attribute['values']:
            attribute_value = val_binder.to_internal(
                magento_value['value_index'], unwrap=True)
            if attribute_value:
                attribute_values |= attribute_value
        if attribute_values:
            return {
                'attribute_id': attribute_values[0].attribute_id.id,
                'value_ids': [(6, 0, attribute_values.ids)],
                }

    def _prepare_attr_lines(self, binding, magento_attributes):
        attribute_line_vals = []
        for attribute in magento_attributes:
            vals = self._prepare_attribute_vals(attribute)
            if vals:
                line = self.env['product.attribute.line'].search([
                    ('attribute_id.id', '=', vals.get('attribute_id')),
                    ('product_tmpl_id.id', '=', binding.odoo_id.id)
                ])
                if line:
                    attribute_line_vals.append((1, line.id, vals))
                else:
                    attribute_line_vals.append((0, 0, vals))
        return attribute_line_vals

    def _after_import(self, binding):
        attrs = self.backend_adapter.list_attributes(binding.external_id)

        attr_importer = self.component(
            usage='record.importer',
            model_name='magento.product.attribute')

        for attribute in attrs:
            attr_importer.run(attribute)

        lines = self._prepare_attr_lines(binding, attrs)
        binding.write({'attribute_line_ids': lines})

        value_binder = self.binder_for('magento.product.attribute.value')
        product_binder = self.binder_for('magento.product.product')

        variants = self.backend_adapter.list_variants(binding.external_id)
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
            if template.id != binding.odoo_id.id:
                vals['product_tmpl_id'] = binding.odoo_id.id
            product.write(vals)
            if not template.product_variant_ids:
                template.unlink()
            # else:
            #     if template.id != binding.odoo_id.id:
            #         raise MappingError(
            #             "The template for the product {} (sku {})"
            #             " has many variants".format(
            #                 product.default_code, variant['sku']))
        super(TemplateImporter, self)._after_import(binding)

    def run(self, external_id, force=True):
        super(TemplateImporter, self).run(external_id, True)
