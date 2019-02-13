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
from odoo.addons.connector.components.mapper import (
    mapping, 
    only_create, 
    ImportMapChild
    )
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

# ========== USELESS PART ? replaced by skip item on map child    
#     def _attribute_value_exists(self, value):
#         att_ids = self.env['product.attribute'].search(
#             [('name', '=', attribute)]
#             )
#         if len(att_ids) == 0:
#             return False
#         return att_ids[0]
#     
#     @only_create
#     @mapping
#     def get_value_id(self, record):
#         value_id = self._attribute_value_exists(
#             self._get_magento_value_external_id(record)['name'])
#         if value_id and len(value_id) == 1 :
#             return {'odoo_id': value_id.id}
#         return {}
#     
#     def _get_magento_value_external_id(self, map_record, values):
#         if map_record.parent:
#             external_id = str(values.get('external_id'))
#             external_id_parent = str(map_record.parent.source.get('attribute_id'))
#             return external_id_parent + '_' + external_id
# =============
    
    def finalize(self, map_record, values):
        if map_record.parent:
            external_id = str(values.get('external_id'))
            external_id_parent = str(map_record.parent.source.get('attribute_id'))
            values.update({'external_id': external_id_parent + '_' + external_id }) 
        return values

class MagentoAttributeValueChildImporter(Component):
    _name = 'magento.product.attribute.value.child.mapper'
    _inherit = 'base.map.child.import'
    _apply_on = 'magento.product.attribute.value'
    
    def skip_item(self, map_record):
        if map_record.parent:
            external_id = str(map_record.source.get('value'))
            external_id_parent = str(map_record.parent.source.get('attribute_id'))
            external_id = external_id_parent + '_' + external_id 
            value_count = self.env['magento.product.attribute.value'].search_count(
                [('external_id', '=', external_id)])
            if value_count >= 1:
                return True
        if map_record.source.get('value') == '':
            return True
    