# -*- coding: utf-8 -*-
# Copyright 2017 Akretion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping


class ProductAttributeValueBatchImporter(Component):
    """ Import the Magento Product Attributes.
    """
    _name = 'magento.product.attribute.value.batch.importer'
    _inherit = 'magento.direct.batch.importer'
    _apply_on = ['magento.product.attribute.value']

    def run(self, filters=None):
        """ Run the synchronization """
        for value in filters['values']:
            value['magento_attribute'] = filters['magento_attribute']
            value['product_id'] = filters['product_id']
            self._import_record(value)


class ProductAttributeValueImporter(Component):
    _name = 'magento.product.attribute.value.importer'
    _inherit = 'magento.importer'
    _apply_on = ['magento.product.attribute.value']

    def _get_magento_data(self, storeview_id=None):
        """
        In this case, the magento_record contains all the data to insert
        """
        return self.magento_record

    def _after_import(self, binding):
        self.env['magento.product.attribute.price'].import_batch(
            self.backend_record,
            {
                'price': self.magento_record,
                'magento_value': binding,
                'product_id': self.magento_record['product_id']
            }
        )

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
        if not record.get('magento_attribute'):
            return

        return {
            'attribute_id': record.get('magento_attribute').odoo_id.id,
            'magento_attribute_id': record.get('magento_attribute').id,
            }
