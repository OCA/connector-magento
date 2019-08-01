# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create
import uuid

_logger = logging.getLogger(__name__)


class AttributeBatchImporter(Component):
    """ Import the Magento Products attributes.

    For every product attributes in the list, a delayed job is created.
    Import from a date
    """
    _name = 'magento.product.attribute.batch.importer'
    _inherit = 'magento.delayed.batch.importer'
    _apply_on = ['magento.product.attribute']
    

class AttributeImporter(Component):
    _name = 'magento.product.attribute.import'
    _inherit = ['magento.importer']
    _magento_id_field = 'attribute_id'

    def _before_import(self):
        record = self.magento_record
        # Check for duplicate values here
        existing_values = []
        existing_names = []
        for i in range(len(record['options'])):
            value = record['options'][i]
            if value['value'] in existing_values:
                raise Exception('Value %s is a duplicate in %s' % (value['value'], record['default_frontend_label']))
            existing_values.append(value['value'])
            if value['label'] in existing_names and self.backend_record.rename_duplicate_values:
                self.magento_record['options'][i]['label'] = "%s (%s)" % (value['label'], str(uuid.uuid4()))
            elif value['label'] in existing_names and not self.backend_record.rename_duplicate_values:
                raise Exception('Value %s is a duplicate in %s' % (value['label'], record['default_frontend_label']))
            existing_names.append(value['label'])


    def _update(self, binding, data):
        """ Update an OpenERP record """
        # special check on data before import
        self._validate_data(data)
        binding.with_context(connector_no_export=True).write(data)
        _logger.debug('%d updated from magento %s', binding, self.external_id)
        record = self.magento_record
        values = [r['value'] for r in record['options']]
        _logger.info("Got values from magento: %s", values)
        odoo_magento_values = self.env['magento.product.attribute.value'].search([
            ('magento_attribute_id', '=', binding.id),
            ('code', 'not in', values),
        ])
        _logger.info("Got following odoo magento values %s to delete: %r", [
            ('magento_attribute_id', '=', binding.id),
            ('code', 'not in', values),
        ], odoo_magento_values)
        odoo_magento_values.with_context(connector_no_export=True).unlink()
        return


class AttributeImportMapper(Component):
    _name = 'magento.product.attribute.import.mapper'
    _inherit = 'magento.import.mapper'
    _apply_on = ['magento.product.attribute']

    direct = [
              ('attribute_code', 'attribute_code'),
              ('attribute_id', 'attribute_id'),
              ('attribute_id', 'external_id'),
              ('frontend_input', 'frontend_input')]
    
    children = [
        ('options', 'magento_attribute_value_ids', 'magento.product.attribute.value'),
    ]
    
    
    def _attribute_exists(self, attribute):
        att_ids = self.env['product.attribute'].search(
            [('name', '=', attribute)]
            )
        if len(att_ids) == 0:
            return False
        return att_ids[0]
        
    
    @only_create
    @mapping
    def get_att_id(self, record):
        # Check if we want to always create new odoo attributes
        if self.backend_record.always_create_new_attributes:
            return {}
        # Else search for existing attribute
        att_id = self._attribute_exists(self._get_name(record)['name'])
        if att_id and len(att_id) == 1:
            return {'odoo_id': att_id.id}
        return {}
    
    @mapping
    def _get_name(self, record):
        name = record['attribute_code']
        if 'default_frontend_label' in record and record['default_frontend_label']:
            name = record['default_frontend_label'] 
        return {'name': name}
    
    @only_create
    @mapping
    def create_variant(self, record):
        # Is by default False - will get set as soon as this attribute appears in a configureable product
        return {'create_variant': False}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}
    
    @mapping
    def odoo_id(self, record):
        """ Will bind the attribute to an existing one with the same code """
        attribute = self.env['magento.product.attribute'].search(
            [('attribute_code', '=', record['attribute_code']),('backend_id', '=', self.backend_record.id)], limit=1)
        if attribute:
            return {'odoo_id': attribute.odoo_id.id}
