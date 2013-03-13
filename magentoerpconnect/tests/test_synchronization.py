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
import magento

import openerp.addons.connector as connector
from openerp.addons.connector.connector import ConnectorUnit
from openerp.addons.magentoerpconnect.queue import job
import openerp.tests.common as common

DB = common.DB
ADMIN_USER_ID = common.ADMIN_USER_ID

def magento_responses(method, args):
    # TODO: a dict is better
    if method == 'ol_websites.search':
        return [1]
    elif method == 'ol_websites.info' and args == [1]:
        return {'code': 'base',
                'name': 'Main Website Test',
                'website_id': '1',
                'is_default': '1',
                'sort_order': '0',
                'default_group_id': '1'}
    elif method == 'ol_groups.search':
        return [1, 2]
    elif method == 'ol_groups.info' and args == [1]:
        return {'default_store_id': '1',
                'group_id': '1',
                'website_id': '1',
                'name': 'Main Website Store Test',
                'root_category_id': '2'}
    elif method == 'ol_groups.info' and args == [2]:
        return {'default_store_id': '2',
                'group_id': '2',
                'website_id': '1',
                'name': 'Shop 2 Test',
                'root_category_id': '2'}
    elif method == 'ol_storeviews.search':
        return [1, 2]
    elif method == 'ol_storeviews.info' and args == [1]:
        return {'code': 'default',
                'store_id': '1',
                'website_id': '1',
                'is_active': '1',
                'sort_order': '0',
                'group_id': '1',
                'name': 'Default Store View Test'}
    elif method == 'ol_storeviews.info' and args == [2]:
        return {'code': 'sv2',
                'store_id': '2',
                'website_id': '1',
                'is_active': '1',
                'sort_order': '0',
                'group_id': '2',
                'name': 'Store View 2 Test'}
    elif method == 'catalog_category.tree':
        return {'name': 'Category parent test',
                'category_id': '1',
                'children': [
                    {'name': 'Child level 1 Test',
                     'category_id': '3',
                     'children': [
                        {'name': 'Child 1 level 2 Test',
                         'category_id': '10',
                         'children': []},
                        {'name': 'Child 2 level 2 Test',
                         'category_id': '13',
                         'children': []}]
                    }]}
    elif method == 'catalog_category.info' and args == [1]:
        return {'description': 'Description 1 Test',
                'name': 'Category parent test',
                'category_id': '1',}
    elif method == 'catalog_category.info' and args == [3]:
        return {'description': 'Description 2 Test',
                'name': 'Category child level 1 test',
                'category_id': '3',}
    elif method == 'catalog_category.info' and args == [10]:
        return {'description': 'Description 3 Test',
                'name': 'Category 1 child level 2 test',
                'category_id': '10',}
    elif method == 'catalog_category.info' and args == [13]:
        return {'description': 'Description 1 Test',
                'name': 'Category 2 child level 2 test',
                'category_id': '13',}

class test_import_magento(common.SingleTransactionCase):
    """ Test the imports from a Magento Mock """

    def setUp(self):
        super(test_import_magento, self).setUp()
        self.backend_model = self.registry('magento.backend')
        self.session = connector.ConnectorSession(self.cr, self.uid)

    def test_00_import_backend(self):
        backend_id = self.backend_model.create(
                self.cr,
                self.uid,
                {'name': 'Test Magento',
                 'type': 'magento',
                 'version': '1.7',
                 'location': 'nearby',
                 'username': 'guewen',
                 'password': '42'})

        with mock.patch('magento.API') as API:
            api_mock = mock.MagicMock(name='magento.api')
            API.return_value = api_mock
            api_mock.__enter__.return_value = api_mock
            api_mock.call.side_effect = magento_responses
            job.import_batch(self.session, 'magento.website', backend_id)
            job.import_batch(self.session, 'magento.store', backend_id)
            job.import_batch(self.session, 'magento.storeview', backend_id)
            job.import_batch(self.session, 'magento.product.category', backend_id)


        website_model = self.registry('magento.website')
        website_ids = website_model.search(self.cr,
                                           self.uid,
                                           [('name', '=', 'Main Website Test')])
        self.assertEqual(len(website_ids), 1)
        website = website_model.browse(self.cr,
                                       self.uid,
                                       website_ids[0])

        self.assertEqual(len(website.store_ids), 2)

        store1, store2 = website.store_ids

        self.assertEqual(store1.name, 'Main Website Store Test')
        self.assertEqual(store2.name, 'Shop 2 Test')

        self.assertEqual(len(store1.storeview_ids), 1)
        self.assertEqual(len(store2.storeview_ids), 1)

        storeview1 = store1.storeview_ids[0]
        storeview2 = store2.storeview_ids[0]

        self.assertEqual(storeview1.name, 'Default Store View Test')
        self.assertEqual(storeview2.name, 'Store View 2 Test')

    def test_10_import_product_category(self):
        backend_id = self.backend_model.create(
                self.cr,
                self.uid,
                {'name': 'Test Magento',
                 'type': 'magento',
                 'version': '1.7',
                 'location': 'nearby',
                 'username': 'guewen',
                 'password': '42'})

        with mock.patch('magento.API') as API:
            api_mock = mock.MagicMock(name='magento.api')
            API.return_value = api_mock
            api_mock.__enter__.return_value = api_mock
            api_mock.call.side_effect = magento_responses
            job.import_batch(self.session, 'magento.product.category', backend_id)

        category_model =self.registry('magento.product.category')
        category_ids = category_model.search(self.cr,
                                             self.uid)
        self.assertEqual(len(category_ids), 4)
        category_ids.sort()
        first_category = category_model.browse(self.cr,
                                              self.uid,
                                              category_ids[0])
        self.assertEqual(first_category.name, 'Category parent test')
        self.assertEqual(first_category.description, 'Description 1 Test')

        self.assertEqual(len(first_category.child_ids), 1)

        category_lvl1 = first_category.child_ids[0]

        self.assertEqual(category_lvl1.name, 'Category child level 1 test')
        self.assertEqual(category_lvl1.description, 'Description 2 Test')
        self.assertEqual(category_lvl1.parent_id, fisrt_category.openerp_id)
        self.assertEqual(category_lvl1.magento_parent_id, first_category.id)
        self.assertEqual(len(category_lvl1.child_ids), 2)

        child1, child2 = category_lvl1.child_ids

        self.assertEqual(child1.name, 'Category child 1 level 2 test')
        self.assertEqual(child1.description, 'Description 3 Test')
        self.assertEqual(child1.parent_id, category_lvl1.openerp_id)
        self.assertEqual(child1.magento_parent_id, category_lvl1.id)

        self.assertEqual(child2.name, 'Category child 2 level 2 test')
        self.assertEqual(child2.description, 'Description 4 Test')
        self.assertEqual(child2.parent_id, category_lvl1.openerp_id)
        self.assertEqual(child2.magento_parent_id, category_lvl1.id)
