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
from functools import partial

from openerp.addons.connector.exception import InvalidDataError
from openerp.addons.magentoerpconnect.unit.import_synchronizer import (
    import_batch,
    import_record)
from openerp.addons.connector.session import ConnectorSession
import openerp.tests.common as common
from .common import (mock_api,
                     mock_urlopen_image)
from .test_data import magento_base_responses

DB = common.DB
ADMIN_USER_ID = common.ADMIN_USER_ID


class test_import_magento(common.SingleTransactionCase):
    """ Test the imports from a Magento Mock.

    The data returned by Magento are those created for the
    demo version of Magento on a standard 1.7 version.
    """

    def setUp(self):
        super(test_import_magento, self).setUp()
        self.backend_model = self.registry('magento.backend')
        self.session = ConnectorSession(self.cr, self.uid)
        data_model = self.registry('ir.model.data')
        self.get_ref = partial(data_model.get_object_reference,
                               self.cr, self.uid)
        backend_ids = self.backend_model.search(
            self.cr, self.uid,
            [('name', '=', 'Test Magento')])
        if backend_ids:
            self.backend_id = backend_ids[0]
        else:
            __, warehouse_id = self.get_ref('stock', 'warehouse0')
            self.backend_id = self.backend_model.create(
                self.cr,
                self.uid,
                {'name': 'Test Magento',
                 'version': '1.7',
                 'location': 'http://anyurl',
                 'username': 'guewen',
                 'warehouse_id': warehouse_id,
                 'password': '42'})
            # payment method needed to import a sale order
            __, workflow_id = self.get_ref('sale_automatic_workflow',
                                           'manual_validation')
            __, journal_id = self.get_ref('account',
                                          'check_journal')
            self.registry('payment.method').create(
                self.cr, self.uid,
                {'name': 'checkmo',
                 'workflow_process_id': workflow_id,
                 'import_rule': 'always',
                 'days_before_cancel': 0,
                 'journal_id': journal_id})

    def test_00_import_backend(self):
        """ Synchronize initial metadata """
        with mock_api(magento_base_responses):
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
        with mock_api(magento_base_responses):
            import_record(self.session, 'magento.product.category',
                          backend_id, 1)

        category_model = self.registry('magento.product.category')
        category_ids = category_model.search(
            self.cr, self.uid, [('backend_id', '=', backend_id)])
        self.assertEqual(len(category_ids), 1)

    def test_11_import_product_category_with_gap(self):
        """ Import of a product category when parent categories are missing """
        backend_id = self.backend_id
        with mock_api(magento_base_responses):
            import_record(self.session, 'magento.product.category',
                          backend_id, 8)

        category_model = self.registry('magento.product.category')
        category_ids = category_model.search(
            self.cr, self.uid, [('backend_id', '=', backend_id)])
        self.assertEqual(len(category_ids), 4)

    def test_12_import_product(self):
        """ Import of a simple product """
        backend_id = self.backend_id
        with mock_api(magento_base_responses):
            with mock_urlopen_image():
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
        with mock_api(magento_base_responses):
            with mock_urlopen_image():
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
        """ Import of a configurable product : no need to import it """
        backend_id = self.backend_id
        with mock_api(magento_base_responses):
            with mock_urlopen_image():
                import_record(self.session,
                              'magento.product.product',
                              backend_id, 126)

        product_model = self.registry('magento.product.product')
        product_ids = product_model.search(self.cr,
                                           self.uid,
                                           [('backend_id', '=', backend_id),
                                            ('magento_id', '=', '126')])
        self.assertEqual(len(product_ids), 0)

    def test_15_import_product_bundle(self):
        """ Bundle should fail: not yet supported """
        backend_id = self.backend_id
        with mock_api(magento_base_responses):
            with self.assertRaises(InvalidDataError):
                import_record(self.session,
                              'magento.product.product',
                              backend_id, 165)

    def test_16_import_product_grouped(self):
        """ Grouped should fail: not yet supported """
        backend_id = self.backend_id
        with mock_api(magento_base_responses):
            with self.assertRaises(InvalidDataError):
                import_record(self.session,
                              'magento.product.product',
                              backend_id, 54)

    def test_16_import_product_virtual(self):
        """ Virtual should fail: not yet supported """
        backend_id = self.backend_id
        with mock_api(magento_base_responses):
            with self.assertRaises(InvalidDataError):
                import_record(self.session,
                              'magento.product.product',
                              backend_id, 144)

    def test_30_import_sale_order(self):
        """ Import a sale order: check """
        backend_id = self.backend_id
        with mock_api(magento_base_responses):
            with mock_urlopen_image():
                import_record(self.session,
                              'magento.sale.order',
                              backend_id, 900000691)
        order_model = self.registry('magento.sale.order')
        order_ids = order_model.search(self.cr,
                                       self.uid,
                                       [('backend_id', '=', backend_id),
                                        ('magento_id', '=', '900000691')])
        self.assertEqual(len(order_ids), 1)

    def test_31_import_sale_order_no_website_id(self):
        """ Import a sale order: website_id is missing (happens with magento...) """
        backend_id = self.backend_id
        with mock_api(magento_base_responses):
            with mock_urlopen_image():
                import_record(self.session,
                              'magento.sale.order',
                              backend_id, 900000692)
        order_model = self.registry('magento.sale.order')
        order_ids = order_model.search(self.cr,
                                       self.uid,
                                       [('backend_id', '=', backend_id),
                                        ('magento_id', '=', '900000692')])
        self.assertEqual(len(order_ids), 1)

    def test_32_import_sale_order_with_prefix(self):
        """ Import a sale order with prefix """
        backend_id = self.backend_id
        self.backend_model.write(self.cr, self.uid, self.backend_id,
                                 {'sale_prefix': 'EC'})
        backend = self.backend_model.browse(self.cr, self.uid, backend_id)
        with mock_api(magento_base_responses):
            with mock_urlopen_image():
                import_record(self.session,
                              'magento.sale.order',
                              backend_id, 900000693)
        order_model = self.registry('magento.sale.order')
        order_ids = order_model.search(self.cr,
                                       self.uid,
                                       [('backend_id', '=', backend_id),
                                        ('magento_id', '=', '900000693')])
        order = order_model.browse(self.cr,
                                   self.uid,
                                   order_ids[0])
        self.assertEqual(order.name, 'EC900000693')
        self.backend_model.write(self.cr, self.uid, self.backend_id,
                                 {'sale_prefix': False})

    def test_33_import_sale_order_with_configurable(self):
        """ Import a sale order with configurable product """
        backend_id = self.backend_id
        with mock_api(magento_base_responses):
            with mock_urlopen_image():
                import_record(self.session,
                              'magento.sale.order',
                              backend_id, 900000694)
        mag_order_model = self.registry('magento.sale.order')
        mag_order_ids = mag_order_model.search(self.cr,
                                               self.uid,
                                               [('backend_id', '=', backend_id),
                                                ('magento_id', '=', '900000694')])
        mag_order_line_model = self.registry('magento.sale.order.line')
        mag_order_line_ids = mag_order_line_model.search(self.cr,
                                                         self.uid,
                                                         [('backend_id', '=', backend_id),
                                                          ('magento_order_id', '=', mag_order_ids[0])])
        self.assertEqual(len(mag_order_ids), 1)
        self.assertEqual(len(mag_order_line_ids), 1)
        order_line_id = mag_order_line_model.read(self.cr,
                                                    self.uid,
                                                    mag_order_line_ids[0],
                                                    ['openerp_id'])['openerp_id']
        order_line_model = self.registry('sale.order.line')
        price_unit = order_line_model.read(self.cr,
                                           self.uid,
                                           order_line_id[0],
                                           ['price_unit'])['price_unit']
        self.assertEqual(price_unit, 41.0500)

    def test_34_import_sale_order_with_taxes_included(self):
        """ Import a sale order with taxes included """
        backend_id = self.backend_id
        self.backend_model.write(self.cr, self.uid, self.backend_id,
                                 {'catalog_price_tax_included': True})
        with mock_api(magento_base_responses):
            with mock_urlopen_image():
                import_record(self.session,
                              'magento.sale.order',
                              backend_id, 900000695)
        mag_order_model = self.registry('magento.sale.order')
        mag_order_ids = mag_order_model.search(self.cr,
                                               self.uid,
                                               [('backend_id', '=', backend_id),
                                                ('magento_id', '=', '900000695')])
        self.assertEqual(len(mag_order_ids), 1)
        order_id = mag_order_model.read(self.cr,
                                        self.uid,
                                        mag_order_ids[0],
                                        ['openerp_id'])['openerp_id']
        order_model = self.registry('sale.order')
        amount_total = order_model.read(self.cr,
                                       self.uid,
                                       order_id[0],
                                       ['amount_total'])['amount_total']
        #97.5 is the amount_total if connector takes correctly included tax prices.
        self.assertEqual(amount_total, 97.5000)
        self.backend_model.write(self.cr, self.uid, self.backend_id,
                                 {'catalog_price_tax_included': False})
