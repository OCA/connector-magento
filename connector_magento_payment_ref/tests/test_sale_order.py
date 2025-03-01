# -*- coding: utf-8 -*-
# Copyright (c) 2015 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from os.path import dirname, join
from odoo.addons.connector_magento.tests.common import MagentoSyncTestCase, \
    recorder

CASSETTE_LIBRARY_DIR = join(dirname(__file__), 'fixtures/cassettes')


class TestSaleOrder(MagentoSyncTestCase):
    """ Test the imports from a Magento Mock.
    """

    def setUp(self):
        super(TestSaleOrder, self).setUp()
        self.payment_method = self.env['account.payment.mode'].search(
            [('name', '=', 'checkmo')],
            limit=1,
        )

    def _import_sale_order(self, increment_id, cassette=True):
        return self._import_record('magento.sale.order',
                                   increment_id, cassette=cassette)

    def test_transaction_id_mapping(self):
        """ Test import of sale order with a payment transaction id"""
        self.payment_method.transaction_id_path = 'payment.transaction_id'
        with recorder.use_cassette('import_sale_order_transaction_id',
                                   cassette_library_dir=CASSETTE_LIBRARY_DIR):
            binding = self._import_sale_order(100000201, cassette=False)
        self.assertEqual(binding.transaction_id, '951')

    def test_transaction_id_mapping_wrong_path(self):
        """ Test import of sale order with a wrong path to the
        transaction_id"""
        self.payment_method.transaction_id_path = 'payment.trans'
        with recorder.use_cassette('import_sale_order_transaction_id',
                                   cassette_library_dir=CASSETTE_LIBRARY_DIR):
            binding = self._import_sale_order(100000201, cassette=False)
        self.assertEqual(binding.transaction_id, False)
