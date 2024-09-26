# -*- coding: utf-8 -*-
# Copyright (c) 2015 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp.addons.magentoerpconnect.tests.test_synchronization import (
    SetUpMagentoSynchronized)
from openerp.addons.magentoerpconnect.tests.data_base import (
    magento_base_responses)
from openerp.addons.magentoerpconnect.unit.import_synchronizer import (
    import_record)
from openerp.addons.magentoerpconnect.tests.common import (
    mock_api,
    mock_urlopen_image)

SALE_ORDER_DATA_MOCK_KEY = ('sales_order.info', (900000695, ))


class TestMagentoSaleImport(SetUpMagentoSynchronized):
    """ Test the imports from a Magento Mock.
    """

    def setUp(self):
        super(TestMagentoSaleImport, self).setUp()
        self.payment_method = self.env['payment.method'].search(
            [('name', '=', 'checkmo')])
        self.payment_method.payment_term_id = False

    def test_transaction_id_mapping(self):
        """ Test import of sale order with a payment transaction id"""
        backend_id = self.backend_id
        self.payment_method.transaction_id_path = 'payment.trans_id'
        data = magento_base_responses[SALE_ORDER_DATA_MOCK_KEY]
        data['payment']['trans_id'] = '123456'
        with mock_api(magento_base_responses):
            with mock_urlopen_image():
                import_record(self.session,
                              'magento.sale.order',
                              backend_id, 900000695)

        order_model = self.env['magento.sale.order']
        mag_order_id = order_model.search([
            ('backend_id', '=', backend_id),
            ('magento_id', '=', '900000695'),
            ])
        self.assertEqual(len(mag_order_id), 1)
        self.assertEqual(mag_order_id.transaction_id, '123456')

    def test_transaction_id_mapping_1(self):
        """ Test import of sale order with wrong path to the payment
        transaction id"""
        backend_id = self.backend_id
        self.payment_method.transaction_id_path = 'payment.tra'
        data = magento_base_responses[SALE_ORDER_DATA_MOCK_KEY]
        data['payment']['trans_id'] = '123456'
        with mock_api(magento_base_responses):
            with mock_urlopen_image():
                import_record(self.session,
                              'magento.sale.order',
                              backend_id, 900000695)

        order_model = self.env['magento.sale.order']
        mag_order_id = order_model.search([
            ('backend_id', '=', backend_id),
            ('magento_id', '=', '900000695'),
            ])
        self.assertEqual(len(mag_order_id), 1)
        self.assertFalse(mag_order_id.transaction_id)
