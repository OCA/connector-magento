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

    direct = [('value_index', 'external_id'),]

    @mapping
    def get_value(self, record):
        name = record['label'] or False
        if not name:
            name = u'False'
        return {'name': name}

    @mapping
    def get_external_id(self, record):
        if record.get('value_index'):
            return {'external_id': record.get('value_index')}
        if record.get('value'):
            return {'external_id': record.get('value_index')}
        if not name:
            name = u'False'
        return {'name': name}

    def finalize(self, map_record, values):
        if map_record.parent:
            external_id = str(values.get('external_id'))
            external_id_parent = str(map_record.parent.source.get('attribute_id'))
            values.update({'external_id': external_id_parent + '_' + external_id })
        return values
