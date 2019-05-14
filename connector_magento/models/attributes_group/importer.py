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


class AttributeGroupBatchImporter(Component):
    """ Import the Magento Attributes Group.

    For every attributes group in the list, a record is generated
    """
    _name = 'magento.product.attributes.group.batch.importer'
    _inherit = 'magento.delayed.batch.importer'
    _apply_on = ['magento.product.attributes.group']

    def run(self, filters=None):
        """ Run the synchronization """
        external_ids = self.backend_adapter.search_read(filters)
        _logger.info('search for attributes set %s returned %s',
                     filters, external_ids)
        importer = self.component(usage='record.importer', model_name='magento.product.attributes.group')
        for external_id in external_ids['items']:
            importer.run(external_id)
            

class AttributeGroupImportMapper(Component):
    _name = 'magento.product.attributes.group.import.mapper'
    _inherit = 'magento.import.mapper'
    _apply_on = 'magento.product.attributes.group'

    direct = [
        ('attribute_group_name', 'name'),
        ('attribute_group_id', 'external_id'),
    ]
    
    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}

    @mapping
    def attribute_set_id(self, record):
        return {'attribute_set_id': self.env['magento.product.attributes.set'].search([
            ('backend_id', '=', self.backend_record.id),
            ('external_id', '=', record['attribute_set_id'])
        ]).id}


class AttributeGroupImporter(Component):
    _name = 'magento.product.attributes.group.importer'
    _inherit = 'magento.importer'
    _apply_on = ['magento.product.attributes.group']
    _magento_id_field = 'attribute_group_id'
