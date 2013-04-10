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

import unittest2
import mock
from contextlib import contextmanager
import magento

from openerp.addons.connector.connector import ConnectorUnit
from openerp.addons.connector.exception import InvalidDataError
from openerp.addons.magentoerpconnect.unit.import_synchronizer import (
        import_batch,
        import_record)
from openerp.addons.connector.session import ConnectorSession
import openerp.tests.common as common
from .test_data import magento_base_responses
from ..unit.backend_adapter import call_to_key

DB = common.DB
ADMIN_USER_ID = common.ADMIN_USER_ID


def get_magento_response(method, arguments):
    key = call_to_key(method, arguments)
    assert key in magento_base_responses, (
        "%s not found in magento responses" % str(key))
    return magento_base_responses[key]


@contextmanager
def mock_api():
    with mock.patch('magento.API') as API:
        api_mock = mock.MagicMock(name='magento.api')
        API.return_value = api_mock
        api_mock.__enter__.return_value = api_mock
        api_mock.call.side_effect = get_magento_response
        yield


class test_import_magento(common.SingleTransactionCase):
    """ Test the imports from a Magento Mock.

    The data returned by Magento are those created for the
    demo version of Magento on a standard 1.7 version.
    """

    def setUp(self):
        super(test_import_magento, self).setUp()
        self.backend_model = self.registry('magento.backend')
        self.session = ConnectorSession(self.cr, self.uid)
        backend_ids = self.backend_model.search(
                self.cr, self.uid,
                [('name', '=', 'Test Magento')])
        if backend_ids:
            self.backend_id = backend_ids[0]
        else:
            data_obj = self.registry('ir.model.data')
            warehouse_id = data_obj.get_object_reference(
                self.cr, self.uid, 'stock', 'warehouse0')[1]
            self.backend_id = self.backend_model.create(
                self.cr,
                self.uid,
                {'name': 'Test Magento',
                 'version': '1.7',
                 'location': 'http://anyurl',
                 'username': 'guewen',
                 'warehouse_id': warehouse_id,
                 'password': '42'})

    def test_00_import_backend(self):
        """ Synchronize initial metadata """
        with mock_api():
            import_batch(self.session, 'magento.website', self.backend_id)
            import_batch(self.session, 'magento.store', self.backend_id)
            import_batch(self.session, 'magento.storeview', self.backend_id)

        website_model = self.registry('magento.website')
        website_ids = website_model.search(self.cr,
                                           self.uid,
                                           [('backend_id', '=', self.backend_id)])
        self.assertEqual(len(website_ids), 2)

        store_model = self.registry('magento.store')
        store_ids = store_model.search(self.cr,
                                       self.uid,
                                       [('backend_id', '=', self.backend_id)])
        self.assertEqual(len(store_ids), 2)

        storeview_model = self.registry('magento.storeview')
        storeview_ids = storeview_model.search(self.cr,
                                               self.uid,
                                               [('backend_id', '=', self.backend_id)])
        self.assertEqual(len(storeview_ids), 4)

        # TODO; install & configure languages on storeviews


    def test_10_import_product_category(self):
        """ Import of a product category """
        backend_id = self.backend_id
        with mock_api():
            import_record(self.session, 'magento.product.category',
                          backend_id, 1)

        category_model = self.registry('magento.product.category')
        category_ids = category_model.search(
                self.cr, self.uid, [('backend_id', '=', backend_id)])
        self.assertEqual(len(category_ids), 1)

    def test_11_import_product_category_with_gap(self):
        """ Import of a product category when parent categories are missing """
        backend_id = self.backend_id
        with mock_api():
            import_record(self.session, 'magento.product.category',
                          backend_id, 8)

        category_model = self.registry('magento.product.category')
        category_ids = category_model.search(
                self.cr, self.uid, [('backend_id', '=', backend_id)])
        self.assertEqual(len(category_ids), 4)

    def test_12_import_product(self):
        """ Import of a simple product """
        backend_id = self.backend_id
        with mock_api():
            import_record(self.session,
                          'magento.product.product',
                          backend_id, 16)

        product_model = self.registry('magento.product.product')
        product_ids = product_model.search(self.cr,
                                           self.uid,
                                           [('backend_id', '=', backend_id),
                                            ('magento_id', '=', '16')])
        self.assertEqual(len(product_ids), 1)

    def test_13_import_product_category_missing(self):
        """ Import of a simple product when the category is missing """
        backend_id = self.backend_id
        with mock_api():
            import_record(self.session,
                          'magento.product.product',
                          backend_id, 25)

        product_model = self.registry('magento.product.product')
        product_ids = product_model.search(self.cr,
                                           self.uid,
                                           [('backend_id', '=', backend_id),
                                            ('magento_id', '=', '25')])
        self.assertEqual(len(product_ids), 1)

    def test_14_import_product_configurable(self):
        """ Configurable should fail: not yet supported """
        backend_id = self.backend_id
        with mock_api():
            with self.assertRaises(InvalidDataError):
                import_record(self.session,
                            'magento.product.product',
                            backend_id, 126)

    def test_15_import_product_bundle(self):
        """ Bundle should fail: not yet supported """
        backend_id = self.backend_id
        with mock_api():
            with self.assertRaises(InvalidDataError):
                import_record(self.session,
                            'magento.product.product',
                            backend_id, 165)

    def test_16_import_product_grouped(self):
        """ Grouped should fail: not yet supported """
        backend_id = self.backend_id
        with mock_api():
            with self.assertRaises(InvalidDataError):
                import_record(self.session,
                            'magento.product.product',
                            backend_id, 54)

    def test_16_import_product_virtual(self):
        """ Virtual should fail: not yet supported """
        backend_id = self.backend_id
        with mock_api():
            with self.assertRaises(InvalidDataError):
                import_record(self.session,
                            'magento.product.product',
                            backend_id, 144)
