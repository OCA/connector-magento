# -*- coding: utf-8 -*-
# Copyright 2017 Akretion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create


class ProductAttributeBatchImporter(Component):
    """ Import the Magento Product Attributes.
    """
    _name = 'magento.product.attribute.batch.importer'
    _inherit = 'magento.direct.batch.importer'
    _apply_on = ['magento.product.attribute']

    def get_updated_attributes(self, record):
        """
            allows to easily override the field used (eg. external_id
            instead of defaul_code)
        """
        return self.backend_adapter.list_attributes(record.external_id)

    def run(self, filters=None):
        """ Run the synchronization """
        record = filters['record']
        updated_attributes = self.get_updated_attributes(record)
        for attribute in updated_attributes:
            self._import_record(attribute)


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

    def _after_import(self, binding):
        self.env['magento.product.attribute.value'].import_batch(
            self.backend_record,
            {
                'values': self.magento_record['values'],
                'magento_attribute': binding,
                'product_id': self.magento_record['product_id'],
            }
        )

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

    def name_origin_field(self):
        """ allows to override the field where the attribute_code is stored"""
        return 'attribute_code'

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}

    @only_create
    @mapping
    def odoo_id(self, record):
        """ Will bind the attribute on a existing attribute
        with the same name """
        attribute = self.env['product.attribute'].search(
            [('name', '=', record[self.name_origin_field()])],
            limit=1,
        )
        if attribute:
            return {'odoo_id': attribute.id}
