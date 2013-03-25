# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2013 Camptocamp SA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import logging

import magento as magentolib
from openerp.addons.connector.unit.backend_adapter import CRUDAdapter
from ..backend import magento

_logger = logging.getLogger(__name__)


class MagentoLocation(object):

    def __init__(self, location, username, password):
        self.location = location
        self.username = username
        self.password = password


class MagentoCRUDAdapter(CRUDAdapter):
    """ External Records Adapter for Magento """

    def __init__(self, environment):
        """

        :param environment: current environment (backend, session, ...)
        :type environment: :py:class:`connector.connector.Environment`
        """
        super(MagentoCRUDAdapter, self).__init__(environment)
        self.magento = MagentoLocation(self.backend_record.location,
                                       self.backend_record.username,
                                       self.backend_record.password)

    def search(self, filters=None):
        """ Search records according to some criterias
        and returns a list of ids """
        raise NotImplementedError

    def read(self, id, attributes=None):
        """ Returns the information of a record """
        raise NotImplementedError

    def search_read(self, filters=None):
        """ Search records according to some criterias
        and returns their information"""
        raise NotImplementedError

    def create(self, data):
        """ Create a record on the external system """
        raise NotImplementedError

    def write(self, id, data):
        """ Update records on the external system """
        raise NotImplementedError

    def delete(self, id):
        """ Delete a record on the external system """
        raise NotImplementedError


class GenericAdapter(MagentoCRUDAdapter):

    _model_name = None
    _magento_model = None

    def search(self, filters=None):
        """ Search records according to some criterias
        and returns a list of ids

        :rtype: list
        """
        with magentolib.API(self.magento.location,
                            self.magento.username,
                            self.magento.password) as api:
            return api.call('%s.search' % self._magento_model,
                            [filters] if filters else [{}])
        return []

    def read(self, id, attributes=None):
        """ Returns the information of a record

        :rtype: dict
        """
        with magentolib.API(self.magento.location,
                            self.magento.username,
                            self.magento.password) as api:
            return api.call('%s.info' % self._magento_model, [id, attributes])
        return {}

    def search_read(self, filters=None):
        """ Search records according to some criterias
        and returns their information"""
        with magentolib.API(self.magento.location,
                            self.magento.username,
                            self.magento.password) as api:
            return api.call('%s.list' % self._magento_model, [filters])
        return []

    def create(self, data):
        """ Create a record on the external system """
        with magentolib.API(self.magento.location,
                            self.magento.username,
                            self.magento.password) as api:
            _logger.debug("api.call(%s.create', [%s])", self._magento_model, data)
            return api.call('%s.create' % self._magento_model, [data])

    def write(self, id, data):
        """ Update records on the external system """
        with magentolib.API(self.magento.location,
                            self.magento.username,
                            self.magento.password) as api:
            _logger.debug("api.call(%s.update', [%s, %s])",
                    self._magento_model, id, data)
            return api.call('%s.update' % self._magento_model, [id, data])

    def delete(self, id):
        """ Delete a record on the external system """
        with magentolib.API(self.magento.location,
                            self.magento.username,
                            self.magento.password) as api:
            _logger.debug("api.call(%s.delete', [%s])",
                    self._magento_model, id)
            return api.call('%s.delete' % self._magento_model, [id])


@magento
class StockPickingAdapter(GenericAdapter):
    _model_name = 'magento.stock.picking.out'
    _magento_model = 'sales_order_shipment'

    def create(self, order_id, items, comment, email, include_comment):
        """ Create a record on the external system """
        with magentolib.API(self.magento.location,
                            self.magento.username,
                            self.magento.password) as api:
            _logger.debug("api.call(%s.create', [%s])", self._magento_model,
                          [order_id, items, comment, email, include_comment])
            return api.call('%s.create' % self._magento_model,
                            [order_id, items, comment, email, include_comment])

    def add_tracking_number(self, magento_id, carrier_code,
                            tracking_title, tracking_number):
        """ Add new tracking number.

        :param magento_id: shipment increment id
        :param carrier_code: code of the carrier on Magento
        :param tracking_title: title displayed on Magento for the tracking
        :param tracking_number: tracking number
        """
        with magentolib.API(self.magento.location,
                            self.magento.username,
                            self.magento.password) as api:
            return api.call('%s.addTrack' % self._magento_model,
                            [magento_id, carrier_code,
                             tracking_title, tracking_number])

    def get_carriers(self, magento_id):
        """ Get the list of carrier codes allowed for the shipping.

        :param magento_id: shipment increment id
        :rtype: list
        """
        with magentolib.API(self.magento.location,
                            self.magento.username,
                            self.magento.password) as api:
            return api.call('%s.getCarriers' % self._magento_model,
                            [magento_id])


@magento
class AccountInvoiceAdapter(GenericAdapter):
    _model_name = 'magento.account.invoice'
    _magento_model = 'sales_order_invoice'

    def create(self, order_increment_id, items, comment, email, include_comment):
        """ Create a record on the external system """
        with magentolib.API(self.magento.location,
                            self.magento.username,
                            self.magento.password) as api:
            _logger.debug("api.call('%s.create', %s)", self._magento_model,
                          [order_increment_id, items, comment, email, include_comment])
            return api.call('%s.create' % self._magento_model,
                            [order_increment_id, items, comment, email, include_comment])

    def search_read(self, filters=None, order_id=None):
        """ Search records according to some criterias
        and returns their information

        :param order_id: 'order_id' field of the magento sale order, this
                         is not the same field than 'increment_id'
        """
        if filters is None:
            filters = {}
        if order_id is not None:
            filters['order_id'] = {'eq': order_id}
        return super(AccountInvoiceAdapter, self).search_read(filters=filters)
