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

import socket
import logging
import xmlrpclib

import magento as magentolib
from openerp.addons.connector.unit.backend_adapter import CRUDAdapter
from openerp.addons.connector.exception import (NetworkRetryableError,
                                                RetryableJobError)
from datetime import datetime
_logger = logging.getLogger(__name__)


MAGENTO_DATETIME_FORMAT = '%Y/%m/%d %H:%M:%S'


recorder = {}


def call_to_key(method, arguments):
    """ Used to 'freeze' the method and arguments of a call to Magento
    so they can be hashable; they will be stored in a dict.

    Used in both the recorder and the tests.
    """
    def freeze(arg):
        if isinstance(arg, dict):
            items = dict((key, freeze(value)) for key, value
                         in arg.iteritems())
            return frozenset(items.iteritems())
        elif isinstance(arg, list):
            return tuple([freeze(item) for item in arg])
        else:
            return arg

    new_args = []
    for arg in arguments:
        new_args.append(freeze(arg))
    return (method, tuple(new_args))


def record(method, arguments, result):
    """ Utility function which can be used to record test data
    during synchronisations. Call it from MagentoCRUDAdapter._call

    Then ``output_recorder`` can be used to write the data recorded
    to a file.
    """
    recorder[call_to_key(method, arguments)] = result


def output_recorder(filename):
    import pprint
    with open(filename, 'w') as f:
        pprint.pprint(recorder, f)
    _logger.debug('recorder written to file %s', filename)


class MagentoLocation(object):

    def __init__(self, location, username, password, version,
                 use_custom_api_path=False, verify_ssl=True):
        self._location = location
        self.username = username
        self.password = password
        self.use_custom_api_path = use_custom_api_path
        self.version = version
        self.verify_ssl = verify_ssl

        self.use_auth_basic = False
        self.auth_basic_username = None
        self.auth_basic_password = None

    @property
    def location(self):
        location = self._location
        if not self.use_auth_basic:
            return location
        assert self.auth_basic_username and self.auth_basic_password
        replacement = "%s:%s@" % (self.auth_basic_username,
                                  self.auth_basic_password)
        location = location.replace('://', '://' + replacement)
        return location


class MagentoCRUDAdapter(CRUDAdapter):
    """ External Records Adapter for Magento """

    def __init__(self, connector_env):
        """

        :param connector_env: current environment (backend, session, ...)
        :type connector_env: :class:`connector.connector.ConnectorEnvironment`
        """
        super(MagentoCRUDAdapter, self).__init__(connector_env)
        backend = self.backend_record
        magento = MagentoLocation(
            backend.location,
            backend.username,
            backend.password,
            backend.version,
            use_custom_api_path=backend.use_custom_api_path,
            verify_ssl=backend.verify_ssl)
        if backend.use_auth_basic:
            magento.use_auth_basic = True
            magento.auth_basic_username = backend.auth_basic_username
            magento.auth_basic_password = backend.auth_basic_password
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

    def _call(self, method, arguments=None):
        try:
            custom_url = self.magento.use_custom_api_path
            protocol = 'rest' if self.magento.version == '2.0' else 'xmlrpc'
            _logger.debug("Start calling Magento api %s", method)
            with magentolib.API(self.magento.location,
                                self.magento.username,
                                self.magento.password,
                                protocol=protocol,
                                full_url=custom_url,
                                verify_ssl=self.magento.verify_ssl) as api:
                # When Magento is installed on PHP 5.4+, the API
                # may return garble data if the arguments contain
                # trailing None.
                if isinstance(arguments, list):
                    while arguments and arguments[-1] is None:
                        arguments.pop()
                start = datetime.now()
                try:
                    result = api.call(method, arguments)
                except:
                    _logger.error("api.call(%s, %s) failed", method, arguments)
                    raise
                else:
                    _logger.debug("api.call(%s, %s) returned %s in %s seconds",
                                  method, arguments, result,
                                  (datetime.now() - start).seconds)
                # Uncomment to record requests/responses in ``recorder``
                # record(method, arguments, result)
                return result
        except (socket.gaierror, socket.error, socket.timeout) as err:
            raise NetworkRetryableError(
                'A network error caused the failure of the job: '
                '%s' % err)
        except xmlrpclib.ProtocolError as err:
            if err.errcode in [502,   # Bad gateway
                               503,   # Service unavailable
                               504]:  # Gateway timeout
                raise RetryableJobError(
                    'A protocol error caused the failure of the job:\n'
                    'URL: %s\n'
                    'HTTP/HTTPS headers: %s\n'
                    'Error code: %d\n'
                    'Error message: %s\n' %
                    (err.url, err.headers, err.errcode, err.errmsg))
            else:
                raise


class GenericAdapter(MagentoCRUDAdapter):

    _model_name = None
    _magento_model = None
    _magento2_model = None
    _magento2_search = None
    _magento2_key = None
    _admin_path = None

    @staticmethod
    def get_searchCriteria(filters):
        """ Craft Magento 2.0 searchCriteria from filters, for example:

        'searchCriteria[filter_groups][0][filters][0][field]': 'website_id',
        'searchCriteria[filter_groups][0][filters][0][value]': '1,2',
        'searchCriteria[filter_groups][0][filters][0][condition_type]': 'in',

        Presumably, filter_groups are joined with AND, while filters in the
        same group are joined with OR (not supported here).
        """
        filters = filters or {}
        res = {}
        count = 0
        expr = 'searchCriteria[filter_groups][%s][filters][0][%s]'
        # http://devdocs.magento.com/guides/v2.0/howdoi/webapi/\
        #    search-criteria.html
        operators = [
            'eq', 'finset', 'from', 'gt', 'gteq', 'in', 'like', 'lt',
            'lteq', 'moreq', 'neq', 'nin', 'notnull', 'null', 'to']
        for field in filters.keys():
            for op in filters[field].keys():
                assert op in operators
                value = filters[field][op]
                if isinstance(value, (list, set)):
                    value = ','.join([unicode(v) for v in value])
                res.update({
                    expr % (count, 'field'): field,
                    expr % (count, 'condition_type'): op,
                    expr % (count, 'value'): value,
                })
                count += 1
        _logger.debug('searchCriteria %s from %s', res, filters)
        return res if res else {'searchCriteria': ''}

    def search(self, filters=None):
        """ Search records according to some criterias
        and returns a list of unique identifiers.

        2.0: query the resource to return the key field for all records.
        Filter out the 0, which designates a magic value, such as the global
        scope for websites, store groups and store views, or the category for
        customers that have not yet logged in.

        /search APIs return a dictionary with a top level 'items' key.
        Repository APIs return a list of items.

        :rtype: list
        """
        if self.magento.version == '2.0':
            key = self._magento2_key or 'id'
            params = {}
            if self._magento2_search:
                params['fields'] = 'items[%s]' % key
                params.update(self.get_searchCriteria(filters))
            else:
                params['fields'] = key
                if filters:
                    raise NotImplementedError  # Unexpected much?
            res = self._call(
                self._magento2_search or self._magento2_model,
                params)
            if 'items' in res:
                res = res['items'] or []
            return [item[key] for item in res if item[key] != 0]

        # 1.x
        return self._call('%s.search' % self._magento_model,
                          [filters] if filters else [{}])

    def read(self, id, attributes=None):
        """ Returns the information of a record

        :rtype: dict
        """
        if self.magento.version == '2.0':

            def escape(term):
                if isinstance(term, basestring):
                    return term.replace('+', '%2B')
                return term

            if attributes:
                raise NotImplementedError
            if self._magento2_key:
                return self._call('%s/%s' % (self._magento2_model, escape(id)),
                                  attributes)
            else:
                res = self._call(self._magento2_model)
                return next(record for record in res if record['id'] == id)

        arguments = [int(id)]
        if attributes:
            # Avoid to pass Null values in attributes. Workaround for
            # https://bugs.launchpad.net/openerp-connector-magento/+bug/1210775
            # When Magento is installed on PHP 5.4 and the compatibility patch
            # http://magento.com/blog/magento-news/magento-now-supports-php-54
            # is not installed, calling info() with None in attributes
            # would return a wrong result (almost empty list of
            # attributes). The right correction is to install the
            # compatibility patch on Magento.
            arguments.append(attributes)
        return self._call('%s.info' % self._magento_model,
                          arguments)

    def search_read(self, filters=None):
        """ Search records according to some criterias
        and returns their information"""
        if self.magento.version == '2.0':
            params = {}
            if self._magento2_search:
                params.update(self.get_searchCriteria(filters))
            else:
                if filters:
                    raise NotImplementedError  # Unexpected much?
            res = self._call(
                self._magento2_search or self._magento2_model,
                params)
            return res

        return self._call('%s.list' % self._magento_model, [filters])

    def create(self, data):
        """ Create a record on the external system """
        return self._call('%s.create' % self._magento_model, [data])

    def write(self, id, data):
        """ Update records on the external system """
        return self._call('%s.update' % self._magento_model,
                          [int(id), data])

    def delete(self, id):
        """ Delete a record on the external system """
        return self._call('%s.delete' % self._magento_model, [int(id)])

    def admin_url(self, id):
        """ Return the URL in the Magento admin for a record """
        if self._admin_path is None:
            raise ValueError('No admin path is defined for this record')
        backend = self.backend_record
        url = backend.admin_location
        if not url:
            raise ValueError('No admin URL configured on the backend.')
        path = self._admin_path.format(model=self._magento_model,
                                       id=id)
        url = url.rstrip('/')
        path = path.lstrip('/')
        url = '/'.join((url, path))
        return url
