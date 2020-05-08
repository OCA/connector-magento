# Copyright 2013-2019 Camptocamp SA
# Copyright 2020 Opener B.V.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import json
from .common import Magento2SyncTestCase, recorder


class TestExportInvoice(Magento2SyncTestCase):
    """ Test the export of an invoice to Magento """

    def setUp(self):
        super(TestExportInvoice, self).setUp()
        self.sale_binding_model = self.env['magento.sale.order']
        self.payment_mode = self.env['account.payment.mode'].search(
            [('name', '=', 'checkmo')],
            limit=1,
        )
        self.pay_account = self.env['account.account'].search(
            [('code', '=', '101501')],
            limit=1,
        )
        self.order_binding = self._import_record(
            'magento.sale.order', '16'
        )
        self.order_binding.payment_mode_id = self.payment_mode
        self.stores = self.backend.mapped('website_ids.store_ids')
        # ignore exceptions on the sale order
        self.order_binding.ignore_exception = True
        self.order_binding.odoo_id.action_confirm()
        invoice_ids = self.order_binding.odoo_id.action_invoice_create()
        assert invoice_ids
        self.invoice_model = self.env['account.invoice']
        self.invoice = self.invoice_model.browse(invoice_ids)

    def test_export_invoice_on_validate_trigger(self):
        """ Trigger export of an invoice: when it is validated """
        # we setup the stores so they export the invoices as soon
        # as they are validated (open)
        self.stores.write({'create_invoice_on': 'open'})
        # prevent to create the job
        with self.mock_with_delay() as (delayable_cls, delayable):
            self._invoice_open()
            self.assertEqual(self.invoice.state, 'open')

            self.assertEqual(len(self.invoice.magento_bind_ids), 1)

            self.assertEqual(1, delayable_cls.call_count)
            delay_args, delay_kwargs = delayable_cls.call_args
            self.assertEqual((self.invoice.magento_bind_ids,), delay_args)

            delayable.export_record.assert_called_with()

        # pay and verify it is NOT called
        with self.mock_with_delay() as (delayable_cls, delayable):
            self._pay_and_reconcile()
            self.assertEqual(self.invoice.state, 'paid')
            self.assertEqual(0, delayable_cls.call_count)

    def test_export_invoice_on_paid_trigger(self):
        """ Trigger export of an invoice: when it is paid """
        # we setup the stores so they export the invoices as soon
        # as they are validated (open)
        self.stores.write({'create_invoice_on': 'paid'})
        # prevent to create the job
        with self.mock_with_delay() as (delayable_cls, delayable):
            self._invoice_open()
            self.assertEqual(self.invoice.state, 'open')

            self.assertEqual(0, delayable_cls.call_count)

        # pay and verify it is NOT called
        with self.mock_with_delay() as (delayable_cls, delayable):
            self._pay_and_reconcile()

            self.assertEqual(self.invoice.state, 'paid')
            self.assertEqual(len(self.invoice.magento_bind_ids), 1)

            self.assertEqual(1, delayable_cls.call_count)

            delay_args, delay_kwargs = delayable_cls.call_args
            self.assertEqual((self.invoice.magento_bind_ids,), delay_args)

            delayable.export_record.assert_called_with()

    def test_export_invoice_on_payment_mode_validate_trigger(self):
        """ Exporting an invoice: when it is validated with payment mode """
        # we setup the stores so they export the invoices as soon
        # as they are validated (open)
        self.payment_mode.write({'create_invoice_on': 'open'})
        # ensure we use the option of the payment method, not store
        self.stores.write({'create_invoice_on': 'paid'})
        with self.mock_with_delay() as (delayable_cls, delayable):
            self._invoice_open()
            self.assertEqual(self.invoice.state, 'open')

            self.assertEqual(len(self.invoice.magento_bind_ids), 1)

            self.assertEqual(1, delayable_cls.call_count)
            delay_args, delay_kwargs = delayable_cls.call_args
            self.assertEqual((self.invoice.magento_bind_ids,), delay_args)

            delayable.export_record.assert_called_with()

        # pay and verify it is NOT called
        with self.mock_with_delay() as (delayable_cls, delayable):
            self._pay_and_reconcile()
            self.assertEqual(self.invoice.state, 'paid')
            self.assertEqual(0, delayable_cls.call_count)

    def test_export_invoice_on_payment_mode_paid_trigger(self):
        """ Exporting an invoice: when it is paid on payment method """
        # we setup the stores so they export the invoices as soon
        # as they are validated (open)
        self.payment_mode.write({'create_invoice_on': 'paid'})
        # ensure we use the option of the payment method, not store
        self.stores.write({'create_invoice_on': 'open'})
        with self.mock_with_delay() as (delayable_cls, delayable):
            self._invoice_open()
            self.assertEqual(self.invoice.state, 'open')
            self.assertEqual(0, delayable_cls.call_count)

        # pay and verify it is NOT called
        with self.mock_with_delay() as (delayable_cls, delayable):
            self._pay_and_reconcile()
            self.assertEqual(self.invoice.state, 'paid')

            self.assertEqual(len(self.invoice.magento_bind_ids), 1)

            self.assertEqual(1, delayable_cls.call_count)

            delay_args, delay_kwargs = delayable_cls.call_args
            self.assertEqual((self.invoice.magento_bind_ids,), delay_args)

            delayable.export_record.assert_called_with()

    def _invoice_open(self):
        self.invoice.action_invoice_open()

    def _pay_and_reconcile(self):
        self.invoice.pay_and_reconcile(
            self.journal,
            pay_amount=self.invoice.amount_total,
            writeoff_acc=self.pay_account,
        )

    def test_export_invoice_job(self):
        """ Exporting an invoice: call towards the Magento API """
        # we setup the payment method so it exports the invoices as soon
        # as they are validated (open)
        self.payment_mode.write({'create_invoice_on': 'open'})
        self.stores.write({'send_invoice_paid_mail': True})

        with self.mock_with_delay():
            self._invoice_open()

        invoice_binding = self.invoice.magento_bind_ids
        self.assertEqual(len(invoice_binding), 1)

        with recorder.use_cassette(
                'test_export_invoice') as cassette:

            invoice_binding.export_record()

        self.assertEqual(1, len(cassette.requests))
        self.assertEqual(
            cassette.requests[0].uri,
            'http://magento/index.php/rest/V1/order/16/invoice')
        self.assertDictEqual(
            json.loads(cassette.requests[0].body.decode('utf-8')),
            {"capture": False,
             "items": [{"orderItemId": "32", "qty": 1.0}],
             "comment": {"comment": "Invoice Created", "isVisibleOnFront": 0},
             "appendComment": False})
        self.assertEqual(invoice_binding.external_id, '4')
