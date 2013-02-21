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

import magento as magentolib
from openerp.addons.connector.unit import CRUDAdapter
from ..backend import magento


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

    # TODO use the magento name instead of the openerp name
    _model_name = 'magento.website'
    _magento_model = None
    _id_field = None

    def search(self, filters=None):
        """ Search records according to some criterias
        and returns a list of ids

        :rtype: list
        """
        with magentolib.API(self.magento.location,
                            self.magento.username,
                            self.magento.password) as api:
            return [int(row[self._id_field]) for row
                    in api.call('%s.list' % self._magento_model,
                                [filters] if filters else [{}])]
        return []

    def read(self, id, attributes=None):
        """ Returns the information of a record

        :rtype: dict
        """
        with magentolib.API(self.magento.location,
                            self.magento.username,
                            self.magento.password) as api:
            return api.call('%s.info' % self._magento_model, [id.id])
        return {}


@magento
class WebsiteAdapter(GenericAdapter):
    # TODO use the magento name instead of the openerp name
    _model_name = 'magento.website'
    _magento_model = 'ol_websites'
    _id_field = 'website_id'


@magento
class StoreAdapter(GenericAdapter):
    _model_name = 'magento.store'
    _magento_model = 'ol_groups'
    _id_field = 'group_id'


@magento
class StoreviewAdapter(GenericAdapter):
    _model_name = 'magento.storeview'
    _magento_model = 'ol_storeviews'
    _id_field = 'store_id'


@magento
class PartnerAdapter(GenericAdapter):
    _model_name = 'res.partner'
    _magento_model = 'customer'
    _id_field = 'customer_id'
