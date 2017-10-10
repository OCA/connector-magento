# -*- coding: utf-8 -*-
# Copyright 2017 Akretion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping
from odoo.addons.connector.exception import MappingError


class ProductAttributeValueBatchImporter(Component):
    """ Import the Magento Product Attributes.
    """
    _name = 'magento.product.attribute.value.batch.importer'
    _inherit = 'magento.delayed.batch.importer'
    _apply_on = ['magento.product.attribute.value']

    def run(self, filters=None):
        """ Run the synchronization """
        for value in filters['values']:
            value['attribute_id'] = filters['attribute_id']
            self._import_record(value, job_options={'priority': 99})


class ProductAttributeValueImporter(Component):
    _name = 'magento.product.attribute.value.importer'
    _inherit = 'magento.importer'
    _apply_on = ['magento.product.attribute.value']

    def _get_magento_data(self, storeview_id=None):
        """
        In this case, the magento_record contains all the data to insert
        """
        return self.magento_record

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
        if not record.get('attribute_id'):
            return
        binder = self.binder_for('magento.product.attribute')
        attribute_binding = binder.to_internal(record['attribute_id'])

        if not attribute_binding:
            raise MappingError("The product attribute with "
                               "magento id %s is not imported." %
                               record['attribute_id'])

        parent = attribute_binding.odoo_id
        return {
            'attribute_id': parent.id,
            'magento_attribute_id': attribute_binding.id,
            }
