# -*- coding: utf-8 -*-
# Copyright 2017 Akretion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping


class ProductAttributeValueImporter(Component):
    _name = 'magento.product.attribute.value.importer'
    _inherit = 'magento.importer'
    _apply_on = ['magento.product.attribute.value']

    def _get_magento_data(self, storeview_id=None):
        """
        In this case, the magento_record contains all the data to insert
        """
        return self.magento_record

    def _update(self, binding, data):
        # Check if a field is different before updating
        modified = False
        for field in data.keys():
            if data[field] != binding[field]:
                modified = True
                break
        if modified:
            super(ProductAttributeValueImporter, self)._update(binding, data)

    def _after_import(self, binding):
        price_importer = self.component(
            usage='record.importer',
            model_name='magento.product.attribute.price')
        price = self.magento_record
        price.update({
            'magento_value': binding,
            'external_id': '{}_{}'.format(
                price['value_index'], price['product_id'])
            })
        price_importer.run(price)

    def run(self, magento_record, force=False):
        self.magento_record = magento_record
        super(ProductAttributeValueImporter, self).run(
            magento_record['value_index'],
            force,
            )


class ProductAttributeValueImportMapper(Component):
    _name = 'magento.product.attribute.value.import.mapper'
    _inherit = 'magento.import.mapper'
    _apply_on = 'magento.product.attribute.value'

    direct = [
        ('label', 'name'),
        ('value_index', 'external_id'),
        ('store_label', 'display_name'),
    ]

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}

    @mapping
    def attribute_id(self, record):
        if not record['magento_attribute']:
            return

        return {
            'attribute_id': record['magento_attribute'].odoo_id.id,
            'magento_attribute_id': record['magento_attribute'].id,
            }

    @mapping
    def odoo_id(self, record):
        """ Will bind the value on a existing one
        with the same name and attribute """
        if not record['magento_attribute']:
            return

        value = self.env['product.attribute.value'].search(
            [('name', '=', record['label']),
             ('attribute_id', '=', record['magento_attribute'].odoo_id.id)],
            limit=1
        )
        if value:
            return {'odoo_id': value.id}
