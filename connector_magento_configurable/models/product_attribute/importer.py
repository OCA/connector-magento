# -*- coding: utf-8 -*-
# Copyright 2017 Akretion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create


class ProductAttributeImporter(Component):
    _name = 'magento.product.attribute.importer'
    _inherit = 'magento.importer'
    _apply_on = ['magento.product.attribute']

    def _get_magento_data(self, storeview_id=None):
        """
        In this case,
        the magento_record already contains all the data to insert,
        no need to make a xmlrpc call
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
            super(ProductAttributeImporter, self)._update(binding, data)

    def _after_import(self, binding):
        value_importer = self.component(
            usage='record.importer',
            model_name='magento.product.attribute.value')
        for value in self.magento_record['values']:
            value.update({'magento_attribute': binding,
                          'product_id': self.magento_record['product_id']})
            value_importer.run(value)

    def run(self, magento_record, force=False):
        self.magento_record = magento_record
        super(ProductAttributeImporter, self).run(
            magento_record['attribute_id'],
            force,
            )


class ProductAttributeImportMapper(Component):
    _name = 'magento.product.attribute.import.mapper'
    _inherit = 'magento.import.mapper'
    _apply_on = 'magento.product.attribute'

    direct = [
        ('attribute_code', 'name'),
        ('attribute_id', 'external_id'),
        ('store_label', 'display_name'),
    ]

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}

    @only_create
    @mapping
    def odoo_id(self, record):
        """ Will bind the attribute on a existing attribute
        with the same name """
        attribute = self.env['product.attribute'].search(
            [('name', '=', record['attribute_code'])],
            limit=1,
        )
        if attribute:
            return {'odoo_id': attribute.id}
