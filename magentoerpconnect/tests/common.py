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

import importlib
import mock
from contextlib import contextmanager
import openerp.tests.common as common
from openerp.addons.connector.session import ConnectorSession
from openerp.addons.magentoerpconnect.unit.import_synchronizer import (
    import_batch,
)
from openerp.addons.magentoerpconnect.unit.backend_adapter import call_to_key
from .data_base import magento_base_responses


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
def mock_job_delay_to_direct(job_path):
    """ Replace the .delay() of a job by a direct call

    job_path is the python path, such as::

      openerp.addons.magentoerpconnect.stock_picking.export_picking_done

    """
    job_module, job_name = job_path.rsplit('.', 1)
    module = importlib.import_module(job_module)
    job_func = getattr(module, job_name, None)
    assert job_func, "The function %s must exist in %s" % (job_name,
                                                           job_module)

    def clean_args_for_func(*args, **kwargs):
        # remove the special args reseved to .delay()
        kwargs.pop('priority', None)
        kwargs.pop('eta', None)
        kwargs.pop('model_name', None)
        kwargs.pop('max_retries', None)
        kwargs.pop('description', None)
        job_func(*args, **kwargs)

    with mock.patch(job_path) as patched_job:
        # call the direct export instead of 'delay()'
        patched_job.delay.side_effect = clean_args_for_func
        yield patched_job


class ChainMap(dict):

    def __init__(self, *maps):
        self._maps = maps

    def __getitem__(self, key):
        for mapping in self._maps:
            try:
                return mapping[key]
            except KeyError:
                pass
        raise KeyError(key)

    def __contains__(self, key):
        try:
            self[key]
        except KeyError:
            return False
        else:
            return True


@contextmanager
def mock_api(responses, key_func=None):
    """
    The responses argument is a dict with the methods and arguments as keys
    and the responses as values. It can also be a list of such dicts.
    When it is a list, the key is searched in the firsts dicts first.

    :param responses: responses returned by Magento
    :type responses: dict
    """
    if isinstance(responses, (list, tuple)):
        responses = ChainMap(*responses)
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


class SetUpMagentoBase(common.TransactionCase):
    """ Base class - Test the imports from a Magento Mock.

    The data returned by Magento are those created for the
    demo version of Magento on a standard 1.7 version.
    """

    def setUp(self):
        super(SetUpMagentoBase, self).setUp()
        self.backend_model = self.env['magento.backend']
        self.session = ConnectorSession(self.env.cr, self.env.uid,
                                        context=self.env.context)
        warehouse = self.env.ref('stock.warehouse0')
        self.backend = self.backend_model.create(
            {'name': 'Test Magento',
             'version': '1.7',
             'location': 'http://anyurl',
             'username': 'guewen',
             'warehouse_id': warehouse.id,
             'password': '42'}
        )
        self.backend_id = self.backend.id
        # payment method needed to import a sale order
        workflow = self.env.ref(
            'sale_automatic_workflow.manual_validation')
        journal = self.env.ref('account.check_journal')
        self.payment_term = self.env.ref('account.'
                                         'account_payment_term_advance')
        self.env['payment.method'].create(
            {'name': 'checkmo',
             'workflow_process_id': workflow.id,
             'import_rule': 'always',
             'days_before_cancel': 0,
             'payment_term_id': self.payment_term.id,
             'journal_id': journal.id})

    def get_magento_helper(self, model_name):
        return MagentoHelper(self.cr, self.registry, model_name)


class SetUpMagentoSynchronized(SetUpMagentoBase):

    def setUp(self):
        super(SetUpMagentoSynchronized, self).setUp()
        with mock_api(magento_base_responses):
            import_batch(self.session, 'magento.website', self.backend_id)
            import_batch(self.session, 'magento.store', self.backend_id)
            import_batch(self.session, 'magento.storeview', self.backend_id)
