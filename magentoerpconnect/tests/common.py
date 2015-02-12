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

"""
Helpers usable in the tests
"""

import mock
from contextlib import contextmanager
from ..unit.backend_adapter import call_to_key


class TestResponder(object):
    """ Used to simulate the calls to Magento.

    For a call (request) to Magento, returns a stored
    response.
    """

    def __init__(self, responses, key_func=None):
        """
        The responses are stored in dict instances.
        The keys are normalized using the ``call_to_key``
        function which transform the request calls in a
        hashable form.

        :param responses: responses returned by Magento
        :param call_to_key: function to build the key
            from the method and arguments
        :type responses: dict
        """
        self._responses = responses
        self._calls = []
        self.call_to_key = key_func or call_to_key

    def __call__(self, method, arguments):
        self._calls.append((method, arguments))
        key = self.call_to_key(method, arguments)
        assert key in self._responses, (
            "%s not found in magento responses" % str(key))
        if hasattr(self._responses[key], '__call__'):
            return self._responses[key]()
        else:
            return self._responses[key]


@contextmanager
def mock_api(responses, key_func=None):
    """
    :param responses: responses returned by Magento
    :type responses: dict
    """
    get_magento_response = TestResponder(responses, key_func=key_func)
    with mock.patch('magento.API') as API:
        api_mock = mock.MagicMock(name='magento.api')
        API.return_value = api_mock
        api_mock.__enter__.return_value = api_mock
        api_mock.call.side_effect = get_magento_response
        yield get_magento_response._calls


class MockResponseImage(object):
    def __init__(self, resp_data, code=200, msg='OK'):
        self.resp_data = resp_data
        self.code = code
        self.msg = msg
        self.headers = {'content-type': 'image/jpeg'}

    def read(self):
        return self.resp_data

    def getcode(self):
        return self.code


@contextmanager
def mock_urlopen_image():
    with mock.patch('urllib2.urlopen') as urlopen:
        urlopen.return_value = MockResponseImage('')
        yield


class MagentoHelper(object):

    def __init__(self, cr, registry, model_name):
        self.cr = cr
        self.model = registry(model_name)

    def get_next_id(self):
        self.cr.execute("SELECT max(magento_id::int) FROM %s " %
                        self.model._table)
        result = self.cr.fetchone()
        if result:
            return int(result[0] or 0) + 1
        else:
            return 1
