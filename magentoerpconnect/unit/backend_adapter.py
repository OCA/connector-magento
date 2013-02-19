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

from openerp.addons.connector.unit import CRUDAdapter
from ..reference import magento
from ..magento_api import Website


class MagentoLocation(object):

    def __init__(self, location, username, password):
        self.location = location
        self.username = username
        self.password = password


class MagentoCRUDAdapter(CRUDAdapter):
    """ External Records Adapter for Magento """

    def __init__(self, reference, magento):
        """
        :param reference: current reference
        :type reference: :py:class:`connector.reference.Reference`
        :param magento: Magento connection information
        :type magento: :py:class:`magentoerpconnect.unit.backend_adapter.MagentoLocation`
        """
        super(MagentoCRUDAdapter, self).__init__(reference)
        self.magento = magento

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


@magento
class WebsiteAdapter(MagentoCRUDAdapter):

    # TODO use the magento name instead of the openerp name
    _model_name = 'magento.website'

    def search(self, filters=None):
        """ Search records according to some criterias
        and returns a list of ids

        :rtype: list
        """
        with Website(self.magento.location,
                     self.magento.username,
                     self.magento.password) as api:
            return [int(row['website_id']) for row in api.list(filters)]
        return []

    def read(self, id, attributes=None):
        """ Returns the information of a record

        :rtype: dict
        """
        with Website(self.magento.location,
                     self.magento.username,
                     self.magento.password) as api:
            return api.info(id)[0]
        return {}
