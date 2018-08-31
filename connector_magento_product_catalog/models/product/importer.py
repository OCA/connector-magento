# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging
import requests
import base64
import sys

from odoo import models, fields, api

from odoo import _
from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping
from odoo.addons.connector.exception import MappingError, InvalidDataError

_logger = logging.getLogger(__name__) 



class ProductImportMapper(Component):
    _inherit = 'magento.product.product.import.mapper'
    
    @mapping
    def attribute_set_id(self, record):
        binder = self.binder_for('magento.product.attributes.set')
        attribute_set = binder.to_internal(record['attribute_set_id'])

        _logger.debug("-------------------------------------------> Import custom attributes %r" % attribute_set)
        link_value = []
        for att in attribute_set.attribute_ids:
            _logger.debug("Import custom att %r" % att)
            
            if record.get(att.name):
                try:
                    searchn = u'_'.join((att.external_id,str(record.get(att.name)))).encode('utf-8')
                except UnicodeEncodeError:
                    searchn = u'_'.join((att.external_id,record.get(att.name))).encode('utf-8')
                att_val = self.env['magento.product.attribute.value'].search(
                    [('external_id', '=', searchn)], limit=1)
                _logger.debug("Import custom att_val %r %r " % (att_val, searchn ))
                if att_val:
                    link_value.append(att_val[0].odoo_id.id)
        #TODO: Switch between standr Odoo class or to the new class
        return {'attribute_set_id': attribute_set.id,'attribute_value_ids': [(6,0,link_value)]}



