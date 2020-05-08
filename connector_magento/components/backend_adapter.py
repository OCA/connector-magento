# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import socket
import logging
import requests
from urllib.parse import quote_plus
import xmlrpc.client

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

    def __init__(self, location, username, password, token, version,
                 verify_ssl, use_custom_api_path=False):
        self._location = location
        self.username = username
        self.password = password
        self.token = token
        self.verify_ssl = verify_ssl
        self.version = version
        self.use_custom_api_path = use_custom_api_path

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


class Magento2Client(object):

    def __init__(self, url, token, verify_ssl=True, use_custom_api_path=False):
        if not use_custom_api_path:
            url += '/' if not url.endswith('/') else ''
            url += 'index.php/rest/V1'
        self._url = url
        self._token = token
        self._verify_ssl = verify_ssl

    def call(self, resource_path, arguments, http_method=None, storeview=None):
        if resource_path is None:
            _logger.exception('Magento2 REST API called without resource path')
            raise NotImplementedError
        url = '%s/%s' % (self._url, resource_path)
        if storeview:
            # https://github.com/magento/magento2/issues/3864
            url = url.replace('/rest/V1/', '/rest/%s/V1/' % storeview)
        if http_method is None:
            http_method = 'get'
        function = getattr(requests, http_method)
        headers = {'Authorization': 'Bearer %s' % self._token}
        kwargs = {'headers': headers}
        if http_method == 'get':
            kwargs['params'] = arguments
        elif arguments is not None:
            kwargs['json'] = arguments
        res = function(url, **kwargs)
        if (res.status_code == 400 and res._content):
            raise requests.HTTPError(
                url, res.status_code, res._content, headers, __name__)
        res.raise_for_status()
        return res.json()


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
            if self._location.version == '1.7':
                api = magentolib.API(
                    self._location.location,
                    self._location.username,
                    self._location.password,
                    full_url=self._location.use_custom_api_path
                )
                api.__enter__()
            else:
                api = Magento2Client(
                    self._location.location,
                    self._location.token,
                    self._location.verify_ssl,
                    use_custom_api_path=self._location.use_custom_api_path
                )
            self._api = api
        return self._api

    def api_call(self, method, arguments, http_method=None, storeview=None):
        """ Adjust available arguments per API """
        if isinstance(self.api, magentolib.API):
            return self.api.call(method, arguments)
        return self.api.call(method, arguments, http_method=http_method,
                             storeview=storeview)

    def __enter__(self):
        # we do nothing, api is lazy
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self._api is not None and hasattr(self._api, '__exit__'):
            self._api.__exit__(exc_type, exc_value, traceback)

    def call(self, method, arguments, http_method=None, storeview=None):
        try:
            # When Magento is installed on PHP 5.4+, the API
            # may return garble data if the arguments contain
            # trailing None.
            if isinstance(arguments, list):
                while arguments and arguments[-1] is None:
                    arguments.pop()
            start = datetime.now()
            try:
                result = self.api_call(
                    method, arguments, http_method=http_method,
                    storeview=storeview)
            except Exception:
                _logger.error("api.call('%s', %s) failed", method, arguments)
                raise
            else:
                _logger.debug("api.call('%s', %s) returned %s in %s seconds",
                              method, arguments, result,
                              (datetime.now() - start).seconds)
            # Uncomment to record requests/responses in ``recorder``
            # record(method, arguments, result)
            return result
        except (socket.gaierror, socket.error, socket.timeout) as err:
            raise NetworkRetryableError(
                'A network error caused the failure of the job: '
                '%s' % err)
        except xmlrpc.client.ProtocolError as err:
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
    # pylint: disable=method-required-super

    _name = 'magento.crud.adapter'
    _inherit = ['base.backend.adapter', 'base.magento.connector']
    _usage = 'backend.adapter'

    def search(self, filters=None):
        """ Search records according to some criterias
        and returns a list of ids """
        raise NotImplementedError

    def read(self, external_id, attributes=None, storeview=None):
        """ Returns the information of a record """
        raise NotImplementedError

    def search_read(self, filters=None):
        """ Search records according to some criterias
        and returns their information"""
        raise NotImplementedError

    def create(self, data):
        """ Create a record on the external system """
        raise NotImplementedError

    def write(self, external_id, data):
        """ Update records on the external system """
        raise NotImplementedError

    def delete(self, external_id):
        """ Delete a record on the external system """
        raise NotImplementedError

    def _call(self, method, arguments=None,
              http_method=None, storeview=None):
        try:
            magento_api = getattr(self.work, 'magento_api')
        except AttributeError:
            raise AttributeError(
                'You must provide a magento_api attribute with a '
                'MagentoAPI instance to be able to use the '
                'Backend Adapter.'
            )
        return magento_api.call(
            method, arguments, http_method=http_method, storeview=storeview)


class GenericAdapter(AbstractComponent):
    # pylint: disable=method-required-super

    _name = 'magento.adapter'
    _inherit = 'magento.crud.adapter'

    _magento_model = None
    _magento2_model = None
    _magento2_search = None
    _magento2_key = None
    _admin_path = None
    _admin2_path = None

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
                    value = ','.join(value)
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
        and returns a list of unique identifiers

        In the case of Magento 2.x: query the resource to return the key field
        for all records. Filter out the 0, which designates a magic value,
        such as the global scope for websites, store groups and store views, or
        the category for customers that have not yet logged in.

        /search APIs return a dictionary with a top level 'items' key.
        Repository APIs return a list of items.

        :rtype: list
        """
        if self.collection.version == '1.7':
            return self._call('%s.search' % self._magento_model,
                              [filters] if filters else [{}])
        key = self._magento2_key or 'id'
        params = {}
        if self._magento2_search:
            params['fields'] = 'items[%s]' % key
            params.update(self.get_searchCriteria(filters))
        else:
            params['fields'] = key
            if filters:
                raise NotImplementedError
        res = self._call(
            self._magento2_search or self._magento2_model,
            params)
        if 'items' in res:
            res = res['items'] or []
        return [item[key] for item in res if item[key] != 0]

    @staticmethod
    def escape(term):
        if isinstance(term, str):
            return quote_plus(term)
        return term

    def read(self, external_id, attributes=None, storeview=None):
        """ Returns the information of a record

        :rtype: dict
        """
        if self.collection.version == '1.7':
            arguments = [int(external_id)]
            # Avoid to pass Null values in attributes. Workaround for
            # https://bugs.launchpad.net/openerp-connector-magento/+bug/1210775
            # When Magento is installed on PHP 5.4 and the compatibility patch
            # http://magento.com/blog/magento-news/magento-now-supports-php-54
            # is not installed, calling info() with None in attributes
            # would return a wrong result (almost empty list of
            # attributes). The right correction is to install the
            # compatibility patch on Magento.
            if attributes:
                arguments.append(attributes)
            return self._call('%s.info' % self._magento_model,
                              arguments, storeview=storeview)

        if attributes:
            raise NotImplementedError
        if self._magento2_key:
            return self._call(
                '%s/%s' % (self._magento2_model, self.escape(external_id)),
                attributes, storeview=storeview)
        res = self._call(self._magento2_model, None)
        return next(record for record in res if record['id'] == external_id)

    def search_read(self, filters=None):
        """ Search records according to some criterias
        and returns their information"""
        if self.collection.version == '1.7':
            return self._call('%s.list' % self._magento_model, [filters])
        params = {}
        if self._magento2_search:
            params.update(self.get_searchCriteria(filters))
        else:
            if filters:
                raise NotImplementedError
        return self._call(
            self._magento2_search or self._magento2_model, params)

    def create(self, data):
        """ Create a record on the external system """
        if self.collection.version == '1.7':
            return self._call('%s.create' % self._magento_model, [data])
        raise NotImplementedError

    def write(self, external_id, data):
        """ Update records on the external system """
        if self.collection.version == '1.7':
            return self._call('%s.update' % self._magento_model,
                              [int(external_id), data])
        raise NotImplementedError

    def delete(self, external_id):
        """ Delete a record on the external system """
        if self.collection.version == '1.7':
            return self._call('%s.delete' % self._magento_model,
                              [int(external_id)])
        raise NotImplementedError

    def admin_url(self, external_id):
        """ Return the URL in the Magento admin for a record """
        backend = self.backend_record
        url = backend.admin_location
        if not url:
            raise ValueError('No admin URL configured on the backend.')
        if hasattr(self.model, '_get_admin_path'):
            admin_path = getattr(self.model, '_get_admin_path')(
                backend, external_id)
        else:
            key = '_admin2_path' if backend.version == '2.0' else '_admin_path'
            admin_path = getattr(self, key)
        if admin_path is None:
            raise ValueError('No admin path is defined for this record')
        path = admin_path.format(model=self._magento_model,
                                 id=external_id)
        url = url.rstrip('/')
        path = path.lstrip('/')
        url = '/'.join((url, path))
        return url
