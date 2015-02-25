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

from openerp.addons.connector.exception import InvalidDataError
from openerp.addons.magentoerpconnect.unit.import_synchronizer import (
    import_batch,
    import_record)
from openerp.addons.connector.session import ConnectorSession
import openerp.tests.common as common
from .common import (mock_api,
                     mock_urlopen_image,
                     MagentoHelper)
from .test_data import magento_base_responses


DB = common.DB
ADMIN_USER_ID = common.ADMIN_USER_ID


class SetUpMagentoBase(common.TransactionCase):
    """ Base class - Test the imports from a Magento Mock.

    The data returned by Magento are those created for the
    demo version of Magento on a standard 1.7 version.
    """

    def setUp(self):
        super(SetUpMagentoBase, self).setUp()
        context = dict(self.env.context, __test_no_commit=True)
        self.backend_model = self.env['magento.backend']
        self.session = ConnectorSession(self.env.cr, self.env.uid,
                                        context=context)
        warehouse = self.env.ref('stock.warehouse0')
        self.backend_id = self.backend_model.create(
            {'name': 'Test Magento',
             'version': '1.7',
             'location': 'http://anyurl',
             'username': 'guewen',
             'warehouse_id': warehouse.id,
             'password': '42'}).id
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


class TestBaseMagento(SetUpMagentoBase):

    def test_00_import_backend(self):
        """ Synchronize initial metadata """
        with mock_api(magento_base_responses):
            import_batch(self.session, 'magento.website', self.backend_id)
            import_batch(self.session, 'magento.store', self.backend_id)
            import_batch(self.session, 'magento.storeview', self.backend_id)

        website_model = self.env['magento.website']
        websites = website_model.search([('backend_id', '=', self.backend_id)])
        self.assertEqual(len(websites), 2)

        store_model = self.env['magento.store']
        stores = store_model.search([('backend_id', '=', self.backend_id)])
        self.assertEqual(len(stores), 2)

        storeview_model = self.env['magento.storeview']
        storeviews = storeview_model.search(
            [('backend_id', '=', self.backend_id)])
        self.assertEqual(len(storeviews), 4)

        # TODO; install & configure languages on storeviews


class SetUpMagentoSynchronized(SetUpMagentoBase):

    def setUp(self):
        super(SetUpMagentoSynchronized, self).setUp()
        with mock_api(magento_base_responses):
            import_batch(self.session, 'magento.website', self.backend_id)
            import_batch(self.session, 'magento.store', self.backend_id)
            import_batch(self.session, 'magento.storeview', self.backend_id)


class TestImportMagento(SetUpMagentoSynchronized):
    """ Test the imports from a Magento Mock.
    """

    def test_10_import_product_category(self):
        """ Import of a product category """
        backend_id = self.backend_id
        with mock_api(magento_base_responses):
            import_record(self.session, 'magento.product.category',
                          backend_id, 1)

        category_model = self.env['magento.product.category']
        categories = category_model.search([('backend_id', '=', backend_id)])
        self.assertEqual(len(categories), 1)

    def test_11_import_product_category_with_gap(self):
        """ Import of a product category when parent categories are missing """
        backend_id = self.backend_id
        with mock_api(magento_base_responses):
            import_record(self.session, 'magento.product.category',
                          backend_id, 8)

        category_model = self.env['magento.product.category']
        categories = category_model.search([('backend_id', '=', backend_id)])
        self.assertEqual(len(categories), 4)

    def test_12_import_product(self):
        """ Import of a simple product """
        backend_id = self.backend_id
        with mock_api(magento_base_responses):
            with mock_urlopen_image():
                import_record(self.session,
                              'magento.product.product',
                              backend_id, 16)

        product_model = self.env['magento.product.product']
        products = product_model.search([('backend_id', '=', backend_id),
                                         ('magento_id', '=', '16')])
        self.assertEqual(len(products), 1)

    def test_13_import_product_category_missing(self):
        """ Import of a simple product when the category is missing """
        backend_id = self.backend_id
        with mock_api(magento_base_responses):
            with mock_urlopen_image():
                import_record(self.session,
                              'magento.product.product',
                              backend_id, 25)

        product_model = self.env['magento.product.product']
        products = product_model.search([('backend_id', '=', backend_id),
                                         ('magento_id', '=', '25')])
        self.assertEqual(len(products), 1)

    def test_14_import_product_configurable(self):
        """ Import of a configurable product : no need to import it """
        backend_id = self.backend_id
        with mock_api(magento_base_responses):
            with mock_urlopen_image():
                import_record(self.session,
                              'magento.product.product',
                              backend_id, 126)

        product_model = self.env['magento.product.product']
        products = product_model.search([('backend_id', '=', backend_id),
                                         ('magento_id', '=', '126')])
        self.assertEqual(len(products), 0)

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
        """ Import sale order: check """
        backend_id = self.backend_id
        with mock_api(magento_base_responses):
            with mock_urlopen_image():
                import_record(self.session,
                              'magento.sale.order',
                              backend_id, 900000691)
        order_model = self.env['magento.sale.order']
        order = order_model.search([('backend_id', '=', backend_id),
                                    ('magento_id', '=', '900000691')])
        self.assertEqual(len(order), 1)
        self.assertEqual(order.payment_term, self.payment_term,
                         "If the payment term is empty, the onchanges have not"
                         "been applied.")

    def test_31_import_sale_order_no_website_id(self):
        """ Import sale order: website_id is missing, happens with magento """
        backend_id = self.backend_id
        with mock_api(magento_base_responses):
            with mock_urlopen_image():
                import_record(self.session,
                              'magento.sale.order',
                              backend_id, 900000692)
        order_model = self.env['magento.sale.order']
        orders = order_model.search([('backend_id', '=', backend_id),
                                     ('magento_id', '=', '900000692')])
        self.assertEqual(len(orders), 1)

    def test_32_import_sale_order_with_prefix(self):
        """ Import sale order with prefix """
        backend = self.backend_model.browse(self.backend_id)
        backend.write({'sale_prefix': 'EC'})
        with mock_api(magento_base_responses):
            with mock_urlopen_image():
                import_record(self.session,
                              'magento.sale.order',
                              backend.id, 900000693)
        order_model = self.env['magento.sale.order']
        orders = order_model.search([('backend_id', '=', backend.id),
                                     ('magento_id', '=', '900000693')])
        order = orders[0]
        self.assertEqual(order.name, 'EC900000693')
        backend.write({'sale_prefix': False})

    def test_33_import_sale_order_with_configurable(self):
        """ Import sale order with configurable product """
        backend_id = self.backend_id
        with mock_api(magento_base_responses):
            with mock_urlopen_image():
                import_record(self.session,
                              'magento.sale.order',
                              backend_id, 900000694)
        mag_order_model = self.env['magento.sale.order']
        mag_orders = mag_order_model.search([('backend_id', '=', backend_id),
                                             ('magento_id', '=', '900000694')])
        mag_order_line_model = self.env['magento.sale.order.line']
        mag_order_lines = mag_order_line_model.search(
            [('backend_id', '=', backend_id),
             ('magento_order_id', '=', mag_orders[0].id)])
        self.assertEqual(len(mag_orders), 1)
        self.assertEqual(len(mag_order_lines), 1)
        order_line = mag_order_lines[0].openerp_id
        price_unit = order_line.price_unit
        self.assertAlmostEqual(price_unit, 41.0500)

    def test_34_import_sale_order_with_taxes_included(self):
        """ Import sale order with taxes included """
        backend_id = self.backend_id
        storeview_model = self.env['magento.storeview']
        storeviews = storeview_model.search([('backend_id', '=', backend_id),
                                             ('magento_id', '=', '1')])
        storeviews.write({'catalog_price_tax_included': True})
        with mock_api(magento_base_responses):
            with mock_urlopen_image():
                import_record(self.session,
                              'magento.sale.order',
                              backend_id, 900000695)
        mag_order_model = self.env['magento.sale.order']
        mag_orders = mag_order_model.search([('backend_id', '=', backend_id),
                                             ('magento_id', '=', '900000695')])
        self.assertEqual(len(mag_orders), 1)
        order = mag_orders[0].openerp_id
        amount_total = order.amount_total
        # 97.5 is the amount_total if connector takes correctly included
        # tax prices.
        self.assertAlmostEqual(amount_total, 97.5000)
        storeviews.write({'catalog_price_tax_included': False})

    def test_35_import_sale_order_with_discount(self):
        """ Import sale order with discounts"""
        backend_id = self.backend_id
        storeview_model = self.env['magento.storeview']
        storeviews = storeview_model.search([('backend_id', '=', backend_id),
                                             ('magento_id', '=', '2')])
        storeviews.write({'catalog_price_tax_included': True})
        with mock_api(magento_base_responses):
            with mock_urlopen_image():
                import_record(self.session,
                              'magento.sale.order',
                              backend_id, 900000696)
        mag_order_model = self.env['magento.sale.order']
        mag_orders = mag_order_model.search([('backend_id', '=', backend_id),
                                             ('magento_id', '=', '900000696')])
        self.assertEqual(len(mag_orders), 1)
        order = mag_orders[0].openerp_id
        self.assertAlmostEqual(order.amount_total, 36.9500)

        for line in order.order_line:
            if line.name == 'Item 1':
                self.assertAlmostEqual(line.discount, 11.904)
            elif line.name == 'Item 2':
                self.assertAlmostEqual(line.discount, 11.957)
            else:
                self.fail('encountered unexpected sale '
                          'order line %s' % line.name)

        storeviews.write({'catalog_price_tax_included': False})
