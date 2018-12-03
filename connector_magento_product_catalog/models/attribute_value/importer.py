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
from odoo.addons.connector.components.mapper import mapping
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
    
    def finalize(self, map_record, values):
        if map_record.parent:
            external_id = str(values.get('external_id'))
            external_id_parent = str(map_record.parent.source.get('attribute_id'))
            values.update({'external_id': external_id_parent + '_' + external_id }) 
        return values
    

    #TODO: 
    ## * Implement _skip method to prevent values with only space to be added
    ## * une @only_create to check possible deplicate values. EG 97_1 seems to be a duplicate values
    