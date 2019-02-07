# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import xmlrpclib
from odoo import models, fields, api
from odoo.addons.queue_job.job import job
from odoo.addons.component.core import Component

from odoo.addons.connector.exception import IDMissingInBackend
from odoo.addons.connector_magento.components.backend_adapter import MAGENTO_DATETIME_FORMAT

_logger = logging.getLogger(__name__)


class PartnerAdapter(Component):
    _inherit = 'magento.partner.adapter'
    _apply_on = 'magento.res.partner'
    
    def get_magento2_datas(self, data, id=0):
        """ Hook to implement in other modules"""
        magento2_datas = {
            'customer': {
                "id": id,
                "group_id": data['group_id'] or 0,
                "gender": 0,
            }
        }
        magento2_datas['customer'].update(data)
        return magento2_datas


    def create(self, data):
        """ Create a record on the external system """
        if self.work.magento_api._location.version == '2.0': 
            data_api2 = self.get_magento2_datas(data)                        
            return super(PartnerAdapter, self).create(data_api2)
        return self._call('%s.create' % self._magento_model,
                          [customer_id, data])

    
    def write(self, id, data):
        """ Create a record on the external system """
        if self.work.magento_api._location.version == '2.0': 
            data_api2 = self.get_magento2_datas(data, id)                        
            return super(PartnerAdapter, self).write(id, data_api2)
        return self._call('%s.create' % self._magento_model,
                          [customer_id, data])


class AddressAdapter(Component):
    _inherit = 'magento.address.adapter'
    _apply_on = 'magento.address'
    
    
    def create(self, data):
        """ Create a record on the external system """
        if self.work.magento_api._location.version == '2.0': 
            data_api2 = self.get_magento2_datas(data)                        
            return super(PartnerAdapter, self).create(data_api2)
        return self._call('%s.create' % self._magento_model,
                          [customer_id, data])

   
