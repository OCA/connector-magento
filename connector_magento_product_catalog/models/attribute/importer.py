# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging
import requests
import base64
import sys

from odoo import _
from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create
from odoo.addons.connector.exception import MappingError, InvalidDataError

_logger = logging.getLogger(__name__)


class AttributeBatchImporter(Component):
    """ Import the Magento Products attributes.

    For every product attributes in the list, a delayed job is created.
    Import from a date
    """
    _name = 'magento.product.attribute.batch.importer'
    _inherit = 'magento.delayed.batch.importer'
    _apply_on = ['magento.product.attribute']
    

            
class AttributeImportMapper(Component):
    _name = 'magento.product.attribute.import.mapper'
    _inherit = 'magento.import.mapper'
    _apply_on = ['magento.product.attribute']

    # TODO :     
    # categ, special_price => minimal_price
    
    direct = [
              ('attribute_code', 'attribute_code'),
              ('attribute_id', 'attribute_id'),
              ('frontend_input', 'frontend_input')]
    
    children = [('options', 'magento_attribute_value_ids', 'magento.product.attribute.value'),
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
        att_id = self._attribute_exists(self._get_name(record)['name'])
        if len(att_id) ==1 :
            return {'odoo_id': att_id.id}
        return {}
    
    @mapping
    def _get_name(self, record):
        name = record['attribute_code']
        if 'default_frontend_label' in record and record['default_frontend_label'] :
            name = record['default_frontend_label'] 
        return {'name': name}
    
    @mapping
    def magento_id(self, record):
        #TODO: get the attribute ID from magento ? Wrong name choice for attribute_id
        return {'magento_id': False}
        
    @mapping
    def create_variant(self, record):
        return {'create_variant': self.env['magento.product.attribute']._is_generate_variant(record['frontend_input'])}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}
    
    @mapping
    def odoo_id(self, record):
        """ Will bind the product to an existing one with the same code """
        attribute = self.env['magento.product.attribute'].search(
            [('attribute_code', '=', record['attribute_code'])], limit=1)
        if attribute:
            return {'odoo_id': attribute.odoo_id.id}


class AttributeImporter(Component):
    _name = 'magento.product.attribute.importer'
    _inherit = 'magento.importer'
    _apply_on = ['magento.product.attribute']
    
    
