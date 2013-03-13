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
from openerp.addons.connector.unit import CRUDAdapter
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
            return api.call('%s.info' % self._magento_model, [id])
        return {}

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
class WebsiteAdapter(GenericAdapter):
    _model_name = 'magento.website'
    _magento_model = 'ol_websites'


@magento
class StoreAdapter(GenericAdapter):
    _model_name = 'magento.store'
    _magento_model = 'ol_groups'


@magento
class StoreviewAdapter(GenericAdapter):
    _model_name = 'magento.storeview'
    _magento_model = 'ol_storeviews'


@magento
class PartnerAdapter(GenericAdapter):
    _model_name = 'magento.res.partner'
    _magento_model = 'customer'

    def search(self, filters=None):
        """ Search records according to some criterias
        and returns a list of ids

        :rtype: list
        """
        with magentolib.API(self.magento.location,
                            self.magento.username,
                            self.magento.password) as api:
            return api.call('ol_customer.search',
                            [filters] if filters else [{}])
        return []


@magento
class PartnerCategoryAdapter(GenericAdapter):
    _model_name = 'magento.res.partner.category'
    _magento_model = 'ol_customer_groups'

    def search(self, filters=None):
        """ Search records according to some criterias
        and returns a list of ids

        :rtype: list
        """
        with magentolib.API(self.magento.location,
                            self.magento.username,
                            self.magento.password) as api:
            return [int(row['customer_group_id']) for row
                       in api.call('%s.list' % self._magento_model,
                                   [filters] if filters else [{}])]
        return []


@magento
class AddressAdapter(GenericAdapter):
    _model_name = 'magento.address'
    _magento_model = 'customer_address'

    def search(self, filters=None):
        """ Search records according to some criterias
        and returns a list of ids

        :rtype: list
        """
        with magentolib.API(self.magento.location,
                            self.magento.username,
                            self.magento.password) as api:
            return [int(row['customer_address_id']) for row
                       in api.call('%s.list' % self._magento_model,
                                   [filters] if filters else [{}])]
        return []


@magento
class ProductCategoryAdapter(GenericAdapter):
    _model_name = 'magento.product.category'
    _magento_model = 'catalog_category'

    def search(self, filters=None):
        """ Search records according to some criterias
        and returns a list of ids

        :rtype: list
        """
        raise NotImplementedError('No search on product categories, '
                                  'use "tree" method')

    def tree(self, parent_id=None, store_view=None):
        """ Returns a tree of product categories

        :rtype: dict
        """
        def filter_ids(tree):
            children = {}
            if tree['children']:
                for node in tree['children']:
                    children.update(filter_ids(node))
            category_id = {tree['category_id']: children}
            return category_id

        with magentolib.API(self.magento.location,
                            self.magento.username,
                            self.magento.password) as api:
            tree = api.call('%s.tree' % self._magento_model, [parent_id,
                                                              store_view])
            return filter_ids(tree)

@magento
class ProductProductAdapter(GenericAdapter):
    _model_name = 'magento.product.product'
    _magento_model = 'catalog_product'

    def search(self, filters=None):
        """ Search records according to some criterias
        and returns a list of ids

        :rtype: list
        """
        with magentolib.API(self.magento.location,
                            self.magento.username,
                            self.magento.password) as api:
            return [int(row['product_id']) for row
                       in api.call('%s.list' % self._magento_model,
                                   [filters] if filters else [{}])]
        return []
