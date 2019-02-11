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

    
class AttributeValueImportMapper(Component):
    _name = 'magento.product.attribute.value.import.mapper'
    _inherit = 'magento.import.mapper'
    _apply_on = ['magento.product.attribute.value']

    # TODO :     categ, special_price => minimal_price
    direct = [
              ('value', 'external_id'),
              ('id', 'code')
              ]
    
    @mapping
    def get_value(self, record):
        name = record['label']
        if not name:
            name = u'False'            
        return {'name' : name }
    
#     @mapping
#     def odoo_id(self, record):
#         value_id = self.env['magento.product.attribute.value'].search(
#             [('backend_id', '=', self.backend_record.backend_id.id),
#              ('external_id', '=',)])
#         return {'odoo_id': }
    
    def _attribute_value_exists(self, value):
        att_ids = self.env['product.attribute'].search(
            [('name', '=', attribute)]
            )
        if len(att_ids) == 0:
            return False
        return att_ids[0]
    
    
    @only_create
    @mapping
    def get_value_id(self, record):
        value_id = self._attribute_value_exists(
            self._get_magento_value_external_id(record)['name'])
        if value_id and len(value_id) == 1 :
            return {'odoo_id': value_id.id}
        return {}
    
    def _get_magento_value_external_id(self, map_record, values):
        if map_record.parent:
            external_id = str(values.get('external_id'))
            external_id_parent = str(map_record.parent.source.get('attribute_id'))
            return external_id_parent + '_' + external_id
    
    def finalize(self, map_record, values):
        if map_record.parent:
            external_id = str(values.get('external_id'))
            external_id_parent = str(map_record.parent.source.get('attribute_id'))
            values.update({'external_id': external_id_parent + '_' + external_id }) 
        return values
    

class MagentoAttributeValueImporter(Component):
    """ Import one AttributeValueImport """

    _name = 'magento.product.attribute.value.importer'
    _inherit = 'magento.importer'
    _apply_on = ['magento.product.attribute.value']
    
    
    def _must_skip(self):
        """ Hook called right after we read the data from the backend.

        If the method returns a message giving a reason for the
        skipping, the import will be interrupted and the message
        recorded in the job (if the import is called directly by the
        job, not by dependencies).

        If it returns None, the import will continue normally.

        :returns: None | str | unicode
        """
        if self.magento_record['type_id'] == 'configurable':
            return _('The configurable product is not imported in Odoo, '
                     'because only the simple products are used in the sales '
                     'orders.')
    

    #TODO: 
    ## * Implement _skip method to prevent values with only space to be added
    ## * une @only_create to check possible deplicate values. EG 97_1 seems to be a duplicate values
    