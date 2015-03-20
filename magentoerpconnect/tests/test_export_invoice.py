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

import mock

import openerp.tests.common as common
from openerp import _
from openerp.addons.connector.session import ConnectorSession
from openerp.addons.magentoerpconnect.unit.import_synchronizer import (
    import_batch,
    import_record)
from .common import (mock_api,
                     mock_job_delay_to_direct,
                     mock_urlopen_image)
from .data_base import magento_base_responses


class TestExportInvoice(common.TransactionCase):
    """ Test the export of an invoice to Magento """

    def setUp(self):
        super(TestExportInvoice, self).setUp()
        backend_model = self.env['magento.backend']
        self.mag_sale_model = self.env['magento.sale.order']
        self.session = ConnectorSession(self.env.cr, self.env.uid,
                                        context=self.env.context)
        warehouse = self.env.ref('stock.warehouse0')
        self.backend = backend = backend_model.create(
            {'name': 'Test Magento',
             'version': '1.7',
             'location': 'http://anyurl',
             'username': 'guewen',
             'warehouse_id': warehouse.id,
             'password': '42'})
        # payment method needed to import a sale order
        workflow = self.env.ref('sale_automatic_workflow.manual_validation')
        journal = self.env.ref('account.check_journal')
        self.payment_method = self.env['payment.method'].create(
            {'name': 'checkmo',
             'create_invoice_on': False,
             'workflow_process_id': workflow.id,
             'import_rule': 'always',
             'journal_id': journal.id})
        self.journal = self.env.ref('account.bank_journal')
        self.pay_account = self.env.ref('account.cash')
        self.period = self.env.ref('account.period_10')
        # import the base informations
        with mock_api(magento_base_responses):
            import_batch(self.session, 'magento.website', backend.id)
            import_batch(self.session, 'magento.store', backend.id)
            import_batch(self.session, 'magento.storeview', backend.id)
            with mock_urlopen_image():
                import_record(self.session,
                              'magento.sale.order',
                              backend.id, 900000691)
        self.stores = self.backend.mapped('website_ids.store_ids')
        sales = self.mag_sale_model.search(
            [('backend_id', '=', backend.id),
             ('magento_id', '=', '900000691')])
        self.assertEqual(len(sales), 1)
        self.mag_sale = sales
        # ignore exceptions on the sale order
        self.mag_sale.ignore_exceptions = True
        self.mag_sale.openerp_id.action_button_confirm()
        sale = self.mag_sale.openerp_id
        invoice_id = sale.action_invoice_create()
        assert invoice_id
        self.invoice_model = self.env['account.invoice']
        self.invoice = self.invoice_model.browse(invoice_id)

    def test_export_invoice_on_validate(self):
        """ Exporting an invoice: when it is validated """
        # we setup the stores so they export the invoices as soon
        # as they are validated (open)
        self.stores.write({'create_invoice_on': 'open'})
        # this is the consumer called when a 'magento.account.invoice'
        # is created, it delay a job to export the invoice
        patched = 'openerp.addons.magentoerpconnect.invoice.export_invoice'
        # mock.patch prevents to create the job
        with mock.patch(patched) as export_invoice:
            self._invoice_open()
            self.assertEquals(len(self.invoice.magento_bind_ids), 1)
            export_invoice.delay.assert_called_with(
                mock.ANY,
                'magento.account.invoice',
                self.invoice.magento_bind_ids[0].id)

        # pay and verify it is NOT called
        # mock.patch prevents to create the job
        with mock.patch(patched) as export_invoice:
            self._pay_and_reconcile()
            self.assertEqual(self.invoice.state, 'paid')
            self.assertFalse(export_invoice.delay.called)

    def test_export_invoice_on_paid(self):
        """ Exporting an invoice: when it is paid """
        # we setup the stores so they export the invoices as soon
        # as they are validated (open)
        self.stores.write({'create_invoice_on': 'paid'})
        # this is the consumer called when a 'magento.account.invoice'
        # is created, it delay a job to export the invoice
        patched = 'openerp.addons.magentoerpconnect.invoice.export_invoice'
        # mock.patch prevents to create the job
        with mock.patch(patched) as export_invoice:
            self._invoice_open()
            self.assertFalse(export_invoice.delay.called)

        # pay and verify it is NOT called
        # mock.patch prevents to create the job
        with mock.patch(patched) as export_invoice:
            self._pay_and_reconcile()
            self.assertEqual(self.invoice.state, 'paid')
            self.assertEquals(len(self.invoice.magento_bind_ids), 1)
            export_invoice.delay.assert_called_with(
                mock.ANY, 'magento.account.invoice',
                self.invoice.magento_bind_ids[0].id)

    def test_export_invoice_on_payment_method_validate(self):
        """ Exporting an invoice: when it is validated with payment method """
        # we setup the stores so they export the invoices as soon
        # as they are validated (open)
        self.payment_method.write({'create_invoice_on': 'open'})
        # ensure we use the option of the payment method, not store
        self.stores.write({'create_invoice_on': 'paid'})
        # this is the consumer called when a 'magento.account.invoice'
        # is created, it delay a job to export the invoice
        patched = 'openerp.addons.magentoerpconnect.invoice.export_invoice'
        # mock.patch prevents to create the job
        with mock.patch(patched) as export_invoice:
            self._invoice_open()

            self.assertEquals(len(self.invoice.magento_bind_ids), 1)
            export_invoice.delay.assert_called_with(
                mock.ANY, 'magento.account.invoice',
                self.invoice.magento_bind_ids[0].id)

        # pay and verify it is NOT called
        # mock.patch prevents to create the job
        with mock.patch(patched) as export_invoice:
            self._pay_and_reconcile()
            self.assertEqual(self.invoice.state, 'paid')
            self.assertFalse(export_invoice.delay.called)

    def test_export_invoice_on_payment_method_paid(self):
        """ Exporting an invoice: when it is paid on payment method """
        # we setup the stores so they export the invoices as soon
        # as they are validated (open)
        self.payment_method.write({'create_invoice_on': 'paid'})
        # ensure we use the option of the payment method, not store
        self.stores.write({'create_invoice_on': 'open'})
        # this is the consumer called when a 'magento.account.invoice'
        # is created, it delay a job to export the invoice
        patched = 'openerp.addons.magentoerpconnect.invoice.export_invoice'
        # mock.patch prevents to create the job
        with mock.patch(patched) as export_invoice:
            self._invoice_open()
            self.assertFalse(export_invoice.delay.called)

        # pay and verify it is NOT called
        # mock.patch prevents to create the job
        with mock.patch(patched) as export_invoice:
            self._pay_and_reconcile()
            self.assertEqual(self.invoice.state, 'paid')
            self.assertEquals(len(self.invoice.magento_bind_ids), 1)
            export_invoice.delay.assert_called_with(
                mock.ANY, 'magento.account.invoice',
                self.invoice.magento_bind_ids[0].id)

    def _invoice_open(self):
        self.invoice.signal_workflow('invoice_open')

    def _pay_and_reconcile(self):
        self.invoice.pay_and_reconcile(
            pay_amount=self.invoice.amount_total,
            pay_account_id=self.pay_account.id,
            period_id=self.period.id,
            pay_journal_id=self.journal.id,
            writeoff_acc_id=self.pay_account.id,
            writeoff_period_id=self.period.id,
            writeoff_journal_id=self.journal.id,
            name="Payment for tests of invoice's exports")

    def test_export_invoice_api(self):
        """ Exporting an invoice: call towards the Magento API """
        job_path = ('openerp.addons.magentoerpconnect.'
                    'invoice.export_invoice')
        response = {
            'sales_order_invoice.create': 987654321,
        }
        # we setup the payment method so it exports the invoices as soon
        # as they are validated (open)
        self.payment_method.write({'create_invoice_on': 'open'})
        self.stores.write({'send_invoice_paid_mail': True})

        with mock_job_delay_to_direct(job_path), \
                mock_api(response, key_func=lambda m, a: m) as calls_done:
            self._invoice_open()

            # Here we check what call with which args has been done by the
            # BackendAdapter towards Magento to create the invoice
            self.assertEqual(len(calls_done), 1)
            method, (mag_order_id, items,
                     comment, email, include_comment) = calls_done[0]
            self.assertEqual(method, 'sales_order_invoice.create')
            self.assertEqual(mag_order_id, '900000691')
            self.assertEqual(items, {'1713': 1.0, '1714': 1.0})
            self.assertEqual(comment, _("Invoice Created"))
            self.assertEqual(email, True)
            self.assertFalse(include_comment)

        self.assertEquals(len(self.invoice.magento_bind_ids), 1)
        binding = self.invoice.magento_bind_ids
        self.assertEquals(binding.magento_id, '987654321')
