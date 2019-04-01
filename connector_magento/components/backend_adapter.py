# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import socket
import logging
import xmlrpclib
import urllib

from odoo.addons.component.core import AbstractComponent
from odoo.addons.queue_job.exception import RetryableJobError
from odoo.addons.connector.exception import NetworkRetryableError
from datetime import datetime

_logger = logging.getLogger(__name__)

try:
    import magento as magentolib
except ImportError:
    _logger.debug("Cannot import 'magento'")


MAGENTO_DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'


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


class MagentoAPI(object):

    def __init__(self, location):
        """
        :param location: Magento location
        :type location: :class:`MagentoLocation`
        """
        self._location = location
        self._api = None

    @property
    def api(self):
        if self._api is None:
            custom_url = self._location.use_custom_api_path
            protocol = 'rest' if self._location.version == '2.0' else 'xmlrpc'
            api = magentolib.API(
                self._location.location,
                self._location.username,
                self._location.password,
                protocol=protocol,
                full_url=custom_url,
                verify_ssl=self._location.verify_ssl,
            )
            api.__enter__()
            self._api = api
        return self._api

    def __enter__(self):
        # we do nothing, api is lazy
        return self

    def __exit__(self, type, value, traceback):
        if self._api is not None:
            self._api.__exit__(type, value, traceback)

    def call(self, method, arguments=None, http_method=None, storeview=None):
        try:
            # When Magento is installed on PHP 5.4+, the API
            # may return garble data if the arguments contain
            # trailing None.
            if isinstance(arguments, list):
                while arguments and arguments[-1] is None:
                    arguments.pop()
            start = datetime.now()
            try:
                result = self.api.call(method, arguments, http_method=http_method, storeview=storeview)
            except:
                _logger.error("api.call('%s', %s, %s, %s) failed", method, arguments, http_method, storeview)
                raise
            else:
                _logger.debug("api.call('%s', %s, %s, %s) returned %s in %s seconds",
                              method, arguments, result, http_method, storeview, 
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


class MagentoCRUDAdapter(AbstractComponent):
    """ External Records Adapter for Magento """

    _name = 'magento.crud.adapter'
    _inherit = ['base.backend.adapter', 'base.magento.connector']
    _usage = 'backend.adapter'

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

    def _call(self, method, arguments=None, http_method=None, storeview=None):
        try:
            magento_api = getattr(self.work, 'magento_api')
        except AttributeError:
            raise AttributeError(
                'You must provide a magento_api attribute with a '
                'MagentoAPI instance to be able to use the '
                'Backend Adapter.'
            )
        _logger.debug("Call magento API with method %s and arguments %s , http_method %s and storeview %s" % (method, arguments, http_method, storeview))
        return magento_api.call(method, arguments, http_method, storeview)


class GenericAdapter(AbstractComponent):

    _name = 'magento.adapter'
    _inherit = 'magento.crud.adapter'

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
        return res if res else {'searchCriteria': '{}'}


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
        if self.work.magento_api._location.version == '2.0':
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

    def read(self, id, attributes=None, storeview_code=None):
        """ Returns the information of a record

        :rtype: dict
        """
        if self.work.magento_api._location.version == '2.0':

            def escape(term):
                if isinstance(term, basestring):
                    return urllib.quote(term.encode('utf-8'), safe='')
                return term

#             if attributes:
#                 raise NotImplementedError
            if self._magento2_key:
                res = self._call('%s/%s' % (self._magento2_model, escape(id)), None, storeview=storeview_code)
                return res
            else:
                res = self._call('%s' % (self._magento2_model), None, storeview=storeview_code)
                return next((
                    record for record in res 
                    if unicode(record['id']).encode('utf-8') == id), 
                    None)

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
        if self.work.magento_api._location.version == '2.0':
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

    def _create_url(self, binding=None):
        return '%s' % self._magento2_model

    def _get_id_from_create(self, result, data=None):
        return result['id']

    def create(self, data, binding=None):
        """ Create a record on the external system """
        if self.work.magento_api._location.version == '2.0': 
            if self._magento2_name:
                new_object = self._call(
                    self._create_url(binding),
                    {self._magento2_name: data}, http_method='post')
            else:
                new_object = self._call(
                    self._create_url(binding),
                    data, http_method='post')
            return self._get_id_from_create(new_object, data)
        return self._call('%s.create' % self._magento_model, [data])

    def _write_url(self, id, binding=None):
        return '%s/%s' % (self._magento2_model, id)

    def write(self, id, data, binding=None):
        """ Update records on the external system """
        if self.work.magento_api._location.version == '2.0':
            if self._magento2_name:
                return self._call(
                    self._write_url(id, binding),
                    {self._magento2_name: data}, http_method='put')
            else:
                return self._call(
                    '%s/%s' % (self._magento2_model, id),
                    data, http_method='put')
        return self._call('%s.update' % self._magento_model,
                          [int(id), data])

    def _delete_url(self, id):
        def escape(term):
            if isinstance(term, basestring):
                return urllib.quote(term.encode('utf-8'), safe='')
            return term

        return '%s/%s' % (self._magento2_model, escape(id))

    def delete(self, id):
        """ Delete a record on the external system """
        if self.work.magento_api._location.version == '2.0':
            res = self._call(self._delete_url(id), http_method="delete")
            return res
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
