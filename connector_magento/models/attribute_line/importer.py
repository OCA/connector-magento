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


class AttributeLineImportMapper(Component):
    _name = 'magento.template.attribute.line.import.mapper'
    _inherit = 'magento.import.mapper'
    _apply_on = ['magento.template.attribute.line']

    children = []
    '''
            u'product_id': 2039,
            u'attribute_id': u'145',
            u'label': u'Size',
            u'values': [
              {
                u'value_index': 172
              },
              {
                u'value_index': 173
              },
              {
                u'value_index': 174
              },
              {
                u'value_index': 175
              },
              {
                u'value_index': 176
              }
            ],
            u'position': 0,
            u'id': 294
    
    '''
    direct = [
        ('label', 'label'),
        ('position', 'position'),
        ('id', 'external_id'),
    ]

    @mapping
    def values(self, record):
        values = record['values']
        binder = self.binder_for('magento.product.attribute.value')
        value_ids = []
        odoo_value_ids = []
        for value in values:
            odoo_magento_value = binder.to_internal(record['attribute_id'] + '_' + str(value['value_index']), unwrap=False)
            if not odoo_magento_value:
                raise MappingError("The product attribute value with "
                                   "magento id %s is not imported." %
                                   value['value_index'])

            value_ids.append((4, odoo_magento_value.id))
            odoo_value_ids.append((4, odoo_magento_value.odoo_id.id))
        return {'magento_product_attribute_value_ids': value_ids, 'value_ids': odoo_value_ids}

    @mapping
    @only_create
    def odoo_id(self, record):
        tbinder = self.binder_for('magento.product.template')
        abinder = self.binder_for('magento.product.attribute')
        template = tbinder.to_internal(record['product_id'], unwrap=True, external_field='magento_id')
        attribute = abinder.to_internal(record['attribute_id'], unwrap=True)
        if not attribute:
            raise MappingError("The product attribute with "
                               "magento id %s is not imported." %
                               record['attribute_id'])
        if not template:
            raise MappingError("The product template with "
                               "magento id %s is not imported." %
                               record['product_id'])
        line = self.env['product.attribute.line'].search([
            ('product_tmpl_id', '=', template.id),
            ('attribute_id', '=', attribute.id),
        ])
        if line:
            return {'odoo_id': line.id}


    @mapping
    def magento_attribute_id(self, record):
        binder = self.binder_for('magento.product.attribute')
        attribute = binder.to_internal(record['attribute_id'], unwrap=False)
        if not attribute:
            raise MappingError("The product attribute with "
                               "magento id %s is not imported." %
                               record['attribute_id'])
        return {'magento_attribute_id': attribute.id}
