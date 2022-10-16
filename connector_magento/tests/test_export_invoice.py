# Copyright 2013-2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from .common import MagentoSyncTestCase, recorder


class TestExportInvoice(MagentoSyncTestCase):
    """ Test the export of an invoice to Magento """

    @classmethod
    def setUpClass(cls):
        super(TestExportInvoice, cls).setUpClass()
        cls.sale_binding_model = cls.env['magento.sale.order']
        cls.payment_mode = cls.env['account.payment.mode'].search(
            [('name', '=', 'checkmo')],
            limit=1,
        )
        cls.pay_account = cls.env['account.account'].search(
            [('code', '=', '101501')],
            limit=1,
        )
        cls.order_binding = cls._import_record(
            'magento.sale.order', '145000008'
        )
        cls.order_binding.payment_mode_id = cls.payment_mode
        cls.stores = cls.backend.mapped('website_ids.store_ids')
        # ignore exceptions on the sale order
        cls.order_binding.ignore_exception = True
        cls.order_binding.odoo_id.action_confirm()
        invoice_ids = cls.order_binding.odoo_id.action_invoice_create()
        assert invoice_ids
        cls.invoice_model = cls.env['account.invoice']
        cls.invoice = cls.invoice_model.browse(invoice_ids)

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

        # 1. login, 2. sales_order_invoice.create, 3. endSession
        self.assertEqual(3, len(cassette.requests))

        self.assertEqual(
            ('sales_order_invoice.create',
                ['145000008', {'598': 1.0}, 'Invoice Created', True, False]),
            self.parse_cassette_request(cassette.requests[1].body)
        )
