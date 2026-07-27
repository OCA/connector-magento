# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging
import socket
import xmlrpc.client
from datetime import datetime
from urllib.parse import quote_plus

import magento as magentolib
import requests

from odoo.addons.component.core import AbstractComponent
from odoo.addons.connector.exception import NetworkRetryableError
from odoo.addons.queue_job.exception import RetryableJobError

_logger = logging.getLogger(__name__)

MAGENTO_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


class MagentoLocation:
    def __init__(
        self,
        location,
        username,
        password,
        token,
        version,
        verify_ssl,
        use_custom_api_path=False,
    ):
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
        replacement = f"{self.auth_basic_username}:{self.auth_basic_password}@"
        location = location.replace("://", "://" + replacement)
        return location


class Magento2Client:
    def __init__(self, url, token, verify_ssl=True, use_custom_api_path=False):
        if not use_custom_api_path:
            url += "/" if not url.endswith("/") else ""
            url += "index.php/rest/V1"
        self._url = url
        self._token = token
        self._verify_ssl = verify_ssl

    def call(self, resource_path, arguments, http_method=None, storeview=None):
        if resource_path is None:
            _logger.exception("Magento2 REST API called without resource path")
            raise NotImplementedError
        url = f"{self._url}/{resource_path}"
        if storeview:
            # https://github.com/magento/magento2/issues/3864
            url = url.replace("/rest/V1/", f"/rest/{storeview}/V1/")
        if http_method is None:
            http_method = "get"
        function = getattr(requests, http_method)
        headers = {"Authorization": f"Bearer {self._token}"}
        kwargs = {"headers": headers}
        if http_method == "get":
            kwargs["params"] = arguments
        elif arguments is not None:
            kwargs["json"] = arguments
        res = function(url, **kwargs)
        res.raise_for_status()
        return res.json()


class MagentoAPI:
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
            if self._location.version == "1.7":
                api = magentolib.API(
                    self._location.location,
                    self._location.username,
                    self._location.password,
                    full_url=self._location.use_custom_api_path,
                )
                api.__enter__()
            else:
                api = Magento2Client(
                    self._location.location,
                    self._location.token,
                    self._location.verify_ssl,
                    use_custom_api_path=self._location.use_custom_api_path,
                )
            self._api = api
        return self._api

    def api_call(self, method, arguments, http_method=None, storeview=None):
        """Adjust available arguments per API"""
        if isinstance(self.api, magentolib.API):
            return self.api.call(method, arguments)
        return self.api.call(
            method, arguments, http_method=http_method, storeview=storeview
        )

    def __enter__(self):
        # we do nothing, api is lazy
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self._api is not None and hasattr(self._api, "__exit__"):
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
                    method, arguments, http_method=http_method, storeview=storeview
                )
            except Exception:
                _logger.error("api.call('%s', %s) failed", method, arguments)
                raise
            else:
                _logger.debug(
                    "api.call('%s', %s) returned %s in %s seconds",
                    method,
                    arguments,
                    result,
                    (datetime.now() - start).seconds,
                )
            # Uncomment to record requests/responses in ``recorder``
            # record(method, arguments, result)
            return result
        except (TimeoutError, OSError, socket.gaierror) as err:
            raise NetworkRetryableError(
                "A network error caused the failure of the job: " f"{err}"
            ) from err
        except xmlrpc.client.ProtocolError as err:
            if err.errcode in [
                502,  # Bad gateway
                503,  # Service unavailable
                504,
            ]:  # Gateway timeout
                raise RetryableJobError(
                    "A protocol error caused the failure of the job:\n"
                    f"URL: {err.url}\n"
                    f"HTTP/HTTPS headers: {err.headers}\n"
                    f"Error code: {err.errcode}\n"
                    f"Error message: {err.errmsg}\n"
                ) from err
            else:
                raise


class MagentoCRUDAdapter(AbstractComponent):
    """External Records Adapter for Magento"""

    # pylint: disable=method-required-super

    _name = "magento.crud.adapter"
    _inherit = ["base.backend.adapter", "base.magento.connector"]
    _usage = "backend.adapter"

    def search(self, filters=None):
        """Search records according to some criterias
        and returns a list of ids"""
        raise NotImplementedError

    def read(self, external_id, attributes=None, storeview=None):
        """Returns the information of a record"""
        raise NotImplementedError

    def search_read(self, filters=None):
        """Search records according to some criterias
        and returns their information"""
        raise NotImplementedError

    def create(self, data):
        """Create a record on the external system"""
        raise NotImplementedError

    def write(self, external_id, data):
        """Update records on the external system"""
        raise NotImplementedError

    def delete(self, external_id):
        """Delete a record on the external system"""
        raise NotImplementedError

    def _call(self, method, arguments=None, http_method=None, storeview=None):
        try:
            magento_api = self.work.magento_api
        except AttributeError as err:
            raise AttributeError(
                "You must provide a magento_api attribute with a "
                "MagentoAPI instance to be able to use the "
                "Backend Adapter."
            ) from err
        return magento_api.call(
            method, arguments, http_method=http_method, storeview=storeview
        )


class GenericAdapter(AbstractComponent):
    # pylint: disable=method-required-super

    _name = "magento.adapter"
    _inherit = "magento.crud.adapter"

    _magento_model = None
    _magento2_model = None
    _magento2_search = None
    _magento2_key = None
    _admin_path = None
    _admin2_path = None

    @staticmethod
    def get_searchCriteria(filters):
        """Craft Magento 2.0 searchCriteria from filters, for example:
        'searchCriteria[filter_groups][0][filters][0][field]': 'website_id',
        'searchCriteria[filter_groups][0][filters][0][value]': '1,2',
        'searchCriteria[filter_groups][0][filters][0][condition_type]': 'in',

        Presumably, filter_groups are joined with AND, while filters in the
        same group are joined with OR (not supported here).
        """
        filters = filters or {}
        res = {}
        count = 0
        expr = "searchCriteria[filter_groups][%s][filters][0][%s]"
        # http://devdocs.magento.com/guides/v2.0/howdoi/webapi/\
        #    search-criteria.html
        operators = [
            "eq",
            "finset",
            "from",
            "gt",
            "gteq",
            "in",
            "like",
            "lt",
            "lteq",
            "moreq",
            "neq",
            "nin",
            "notnull",
            "null",
            "to",
        ]
        for field in filters.keys():
            if isinstance(filters[field], dict):
                op_dict = filters[field]
            else:
                op_dict = {"eq": filters[field]}
            for op, value in op_dict.items():
                if op not in operators:
                    op = "eq"
                if isinstance(value, list | set | tuple):
                    value = ",".join(str(v) for v in value)
                    if op == "eq":
                        op = "in"
                res.update(
                    {
                        expr % (count, "field"): field,
                        expr % (count, "condition_type"): op,
                        expr % (count, "value"): str(value),
                    }
                )
                count += 1
        _logger.debug("searchCriteria %s from %s", res, filters)
        return res if res else {"searchCriteria": ""}

    def search(self, filters=None):
        """Search records according to some criterias
        and returns a list of unique identifiers

        In the case of Magento 2.x: query the resource to return the key field
        for all records. Filter out the 0, which designates a magic value,
        such as the global scope for websites, store groups and store views, or
        the category for customers that have not yet logged in.

        /search APIs return a dictionary with a top level 'items' key.
        Repository APIs return a list of items.

        :rtype: list
        """
        if self.collection.version and self.collection.version.startswith("1."):
            return self._call(
                f"{self._magento_model}.search", [filters] if filters else [{}]
            )
        key = self._magento2_key or "id"
        params = {}
        if self._magento2_search:
            params["fields"] = f"items[{key}]"
            params.update(self.get_searchCriteria(filters))
        else:
            params["fields"] = key
            if filters:
                params.update(self.get_searchCriteria(filters))
        res = self._call(self._magento2_search or self._magento2_model, params)
        if isinstance(res, dict) and "items" in res:
            res = res["items"] or []
        elif not isinstance(res, list):
            res = [res] if res else []
        result_ids = []
        for item in res:
            val = item.get(key) if isinstance(item, dict) else item
            if val and val != 0 and val != "0":
                result_ids.append(val)
        return result_ids

    @staticmethod
    def escape(term):
        if isinstance(term, str):
            return quote_plus(term)
        return term

    def read(self, external_id, attributes=None, storeview=None):
        """Returns the information of a record

        :rtype: dict
        """
        if self.collection.version and self.collection.version.startswith("1."):
            arguments = [int(external_id)]
            if attributes:
                arguments.append(attributes)
            return self._call(
                f"{self._magento_model}.info", arguments, storeview=storeview
            )

        if attributes:
            params = (
                self.get_searchCriteria(attributes)
                if isinstance(attributes, dict)
                else {}
            )
        else:
            params = None
        if self._magento2_key:
            return self._call(
                f"{self._magento2_model}/{self.escape(external_id)}",
                params,
                storeview=storeview,
            )
        res = self._call(self._magento2_model, None)
        return next(record for record in res if record["id"] == external_id)

    def search_read(self, filters=None):
        """Search records according to some criterias
        and returns their information"""
        if self.collection.version and self.collection.version.startswith("1."):
            return self._call(f"{self._magento_model}.list", [filters])
        params = {}
        if self._magento2_search:
            params.update(self.get_searchCriteria(filters))
        else:
            if filters:
                params.update(self.get_searchCriteria(filters))
        return self._call(self._magento2_search or self._magento2_model, params)

    def create(self, data):
        """Create a record on the external system"""
        if self.collection.version and self.collection.version.startswith("1."):
            return self._call(f"{self._magento_model}.create", [data])
        res = self._call(self._magento2_model, data, http_method="POST")
        return res.get("id") if isinstance(res, dict) else res

    def write(self, external_id, data):
        """Update records on the external system"""
        if self.collection.version and self.collection.version.startswith("1."):
            return self._call(f"{self._magento_model}.update", [int(external_id), data])
        return self._call(
            f"{self._magento2_model}/{self.escape(external_id)}",
            data,
            http_method="PUT",
        )

    def delete(self, external_id):
        """Delete a record on the external system"""
        if self.collection.version and self.collection.version.startswith("1."):
            return self._call(f"{self._magento_model}.delete", [int(external_id)])
        return self._call(
            f"{self._magento2_model}/{self.escape(external_id)}",
            http_method="DELETE",
        )

    def admin_url(self, external_id):
        """Return the URL in the Magento admin for a record"""
        backend = self.backend_record
        url = backend.admin_location
        if not url:
            raise ValueError("No admin URL configured on the backend.")
        if hasattr(self.model, "_get_admin_path"):
            admin_path = self.model._get_admin_path(backend, external_id)
        else:
            key = "_admin2_path" if backend.version == "2.0" else "_admin_path"
            admin_path = getattr(self, key)
        if admin_path is None:
            raise ValueError("No admin path is defined for this record")
        path = admin_path.format(model=self._magento_model, id=external_id)
        url = url.rstrip("/")
        path = path.lstrip("/")
        url = "/".join((url, path))
        return url
