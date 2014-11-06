# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Chafique DELLI
#    Copyright 2014 AKRETION SA
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

from openerp.addons.magentoerpconnect.unit.export_synchronizer import (
    export_record)
from openerp.addons.magentoerpconnect_catalog.tests.test_attribute_synchronization import (
    SetUpMagentoSynchronizedWithAttribute)
from openerp.addons.magentoerpconnect.tests.common import mock_api


class TestExportMagento(SetUpMagentoSynchronizedWithAttribute):
    """
        Test the exports of Simple and Configurable Products to a Magento Mock.
    """

    def setUp(self):
        super(TestExportMagento, self).setUp()

    def test_export_simple_product(self):
        """ Export a Simple Product: check """
        response = {
            'catalog_product.create': '218'
        }
        with mock_api(response, key_func=lambda m, a: m) as calls_done:
            mag_product_model = self.registry('magento.product.product')

            mag_product_id = mag_product_model.create(self.cr, self.uid, {
                'product_type': 'simple',
                'attribute_set_id': self.default_attr_set_id,
                'default_code': 't-shirt - L - bleu',
                'description': False,
                'visibility': '1',
                'price': 10.0,
                'weight': 0.0,
                'website_ids': (),
                'updated_at': '1970-01-01',
                'categories': (),
                'status': '1',
                'created_at': False,
                'name': 't-shirt taille - L | couleur - bleu',
                'description_sale': False,
                'backend_id': self.backend_id
            })

            export_record(self.session, 'magento.product.product',
                          mag_product_id)
            self.assertEqual(len(calls_done), 1)

            method, data = calls_done[0]
            product_type = data[0]
            attribute_set_id = data[1]
            name = data[2]
            self.assertEqual(method, 'catalog_product.create')
            self.assertEqual(product_type, 'simple')
            self.assertEqual(attribute_set_id, '9')
            self.assertEqual(name, 't-shirt - L - bleu')

    def test_export_configurable_product(self):
        """ Export a Configurable Product: check """

        response = {
            'ol_catalog_product.create': '217'
        }
        with mock_api(response, key_func=lambda m, a: m) as calls_done:
            mag_product_model = self.registry('magento.product.product')

            mag_product_id = mag_product_model.create(self.cr, self.uid, {
                'product_type': 'configurable',
                'attribute_set_id': self.default_attr_set_id,
                'default_code': 't-shirt',
                'description': False,
                'visibility': '1',
                'price': 10.0,
                'weight': 0.0,
                'website_ids': (),
                'updated_at': '1970-01-01',
                'categories': (),
                'status': '1',
                'created_at': False,
                'name': 't-shirt',
                'description_sale': False,
                'backend_id': self.backend_id
            })

            export_record(self.session, 'magento.product.product',
                          mag_product_id)
            self.assertEqual(len(calls_done), 1)

            method, data = calls_done[0]
            product_type = data[0]
            attribute_set_id = data[1]
            name = data[2]
            self.assertEqual(method, 'ol_catalog_product.create')
            self.assertEqual(product_type, 'configurable')
            self.assertEqual(attribute_set_id, '9')
            self.assertEqual(name, 't-shirt')
