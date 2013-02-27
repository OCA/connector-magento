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
            job.import_batch(self.session, backend_id, 'magento.website')
            job.import_batch(self.session, backend_id, 'magento.store')
            job.import_batch(self.session, backend_id, 'magento.storeview')


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
