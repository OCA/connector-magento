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
        "%s not found in magento responses" % key)
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

        storeview_model = self.registry('magento.storeviewview')
        storeview_ids = storeview_model.search(self.cr,
                                               self.uid,
                                               [('backend_id', '=', self.backend_id)])
        self.assertEqual(len(storeview_ids), 4)

        # TODO; install & configure languages on storeviews


    def test_10_import_product_category(self):
        backend_id = self.backend_id

        with mock.patch('magento.API') as API:
            api_mock = mock.MagicMock(name='magento.api')
            API.return_value = api_mock
            api_mock.__enter__.return_value = api_mock
            api_mock.call.side_effect = magento_responses
            import_record(self.session, 'magento.product.category',
                          backend_id, 1)
            import_record(self.session, 'magento.product.category',
                          backend_id, 3)
            import_record(self.session, 'magento.product.category',
                          backend_id, 10)
            import_record(self.session, 'magento.product.category',
                          backend_id, 13)

        category_model = self.registry('magento.product.category')
        category_ids = category_model.search(
                self.cr, self.uid, [('backend_id', '=', backend_id)])
        self.assertEqual(len(category_ids), 4)
        category_ids.sort()
        first_category = category_model.browse(self.cr,
                                               self.uid,
                                               category_ids[0])
        self.assertEqual(first_category.name, 'Category parent test')
        self.assertEqual(first_category.description, 'Description 1 Test')

        self.assertEqual(len(first_category.child_id), 1)

        category_lvl1 = first_category.child_id[0]

        self.assertEqual(category_lvl1.name, 'Category child level 1 test')
        self.assertEqual(category_lvl1.description, 'Description 2 Test')
        self.assertEqual(category_lvl1.parent_id, fisrt_category.openerp_id)
        self.assertEqual(category_lvl1.magento_parent_id, first_category.id)
        self.assertEqual(len(category_lvl1.child_id), 2)

        child1, child2 = category_lvl1.child_id

        self.assertEqual(child1.name, 'Category child 1 level 2 test')
        self.assertEqual(child1.description, 'Description 3 Test')
        self.assertEqual(child1.parent_id, category_lvl1.openerp_id)
        self.assertEqual(child1.magento_parent_id, category_lvl1.id)

        self.assertEqual(child2.name, 'Category child 2 level 2 test')
        self.assertEqual(child2.description, 'Description 4 Test')
        self.assertEqual(child2.parent_id, category_lvl1.openerp_id)
        self.assertEqual(child2.magento_parent_id, category_lvl1.id)
