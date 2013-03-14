# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: David Beal
#    Copyright 2013 Akretion
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

import openerp.tests.common as common
import openerp.addons.connector as connector
from openerp.addons.magentoerpconnect.unit.import_synchronizer import (
        import_record)

DB = common.DB
ADMIN_USER_ID = common.ADMIN_USER_ID


def magento_responses(method, args):
    # TODO: a dict is better
    print method, args
    if method == 'catalog_product.list':
        return [{'product_id': '1'}]
    elif method == 'catalog_product.info' and args == [1, None]:
        return {'product_id': '1',
                'name': 'My Test Product',
                'description': "Mon produit de la mort qui tue",
                'weight': 15,
                'price': 20,
                'cost': 15.25,
                'short_description': 'best product',
                'sku': '12556LKJ99',
                'type_id': 'simple',
                'websites': [],
        }


class test_import_magento(common.SingleTransactionCase):
    """ Test the imports from a Magento Mock """

    def setUp(self):
        super(test_import_magento, self).setUp()
        self.backend_model = self.registry('magento.backend')
        self.session = connector.session.ConnectorSession(self.cr, self.uid)

    def test_00_import_product(self):
        backend_id = self.backend_model.create(
                self.cr,
                self.uid,
                {'name': 'Test Magento product',
                 'type': 'magento',
                 'version': '1.7',
                 'location': 'nearby',
                 'username': 'openerp',
                 'password': 'openerp'})

        with mock.patch('magento.API') as API:
            api_mock = mock.MagicMock(name='magento.api')
            API.return_value = api_mock
            api_mock.__enter__.return_value = api_mock
            api_mock.call.side_effect = magento_responses
            import_record(self.session,
                          'magento.product.product',
                          backend_id,
                          1)

        product_model = self.registry('magento.product.product')
        product_ids = product_model.search(self.cr,
                                           self.uid,
                                           [('name', '=', 'My Test Product')])
        self.assertEqual(len(product_ids), 1)
