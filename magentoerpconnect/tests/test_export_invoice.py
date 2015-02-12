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
from functools import partial

import openerp.tests.common as common
from openerp import netsvc
from openerp.addons.connector.session import ConnectorSession
from openerp.addons.magentoerpconnect.unit.import_synchronizer import (
    import_batch,
    import_record)
from .common import (mock_api,
                     mock_urlopen_image)
from .test_data import magento_base_responses


class test_export_invoice(common.TransactionCase):
    """ Test the export of an invoice to Magento """

    def setUp(self):
        super(test_export_invoice, self).setUp()
        cr, uid = self.cr, self.uid
        backend_model = self.registry('magento.backend')
        self.mag_sale_model = self.registry('magento.sale.order')
        self.session = ConnectorSession(cr, uid)
        self.session.context['__test_no_commit'] = True
        data_model = self.registry('ir.model.data')
        self.get_ref = partial(data_model.get_object_reference,
                               cr, uid)
        __, warehouse_id = self.get_ref('stock', 'warehouse0')
        backend_id = backend_model.create(
            cr,
            uid,
            {'name': 'Test Magento',
                'version': '1.7',
                'location': 'http://anyurl',
                'username': 'guewen',
                'warehouse_id': warehouse_id,
                'password': '42'})
        self.backend = backend_model.browse(cr, uid, backend_id)
        # payment method needed to import a sale order
        __, workflow_id = self.get_ref('sale_automatic_workflow',
                                       'manual_validation')
        __, journal_id = self.get_ref('account',
                                      'check_journal')
        self.payment_method_id = self.registry('payment.method').create(
            cr, uid,
            {'name': 'checkmo',
             'create_invoice_on': False,
             'workflow_process_id': workflow_id,
             'import_rule': 'always',
             'journal_id': journal_id})
        __, self.journal_id = self.get_ref('account', 'bank_journal')
        __, self.pay_account_id = self.get_ref('account', 'cash')
        __, self.period_id = self.get_ref('account', 'period_10')
        # import the base informations
        with mock_api(magento_base_responses):
            import_batch(self.session, 'magento.website', backend_id)
            import_batch(self.session, 'magento.store', backend_id)
            import_batch(self.session, 'magento.storeview', backend_id)
            with mock_urlopen_image():
                import_record(self.session,
                              'magento.sale.order',
                              backend_id, 900000691)
        sale_ids = self.mag_sale_model.search(
            cr, uid,
            [('backend_id', '=', backend_id),
             ('magento_id', '=', '900000691')])
        self.assertEqual(len(sale_ids), 1)
        self.mag_sale = self.mag_sale_model.browse(cr, uid, sale_ids[0])
        # ignore exceptions on the sale order
        self.mag_sale.write({'ignore_exceptions': True})
        self.mag_sale.openerp_id.action_button_confirm()
        self.mag_sale.refresh()  # update to manual state
        self.sale_id = self.mag_sale.openerp_id.id
        sale_obj = self.registry('sale.order')
        invoice_id = sale_obj.action_invoice_create(cr, uid, [self.sale_id])
        assert invoice_id
        self.invoice_model = self.registry('account.invoice')
        self.invoice = self.invoice_model.browse(cr, uid, invoice_id)

    def test_export_invoice_on_validate(self):
        """ Exporting an invoice: when it is validated """
        cr, uid = self.cr, self.uid
        store_ids = [store.id for website in self.backend.website_ids
                     for store in website.store_ids]
        # we setup the stores so they export the invoices as soon
        # as they are validated (open)
        self.registry('magento.store').write(
            cr, uid, store_ids, {'create_invoice_on': 'open'})
        # this is the consumer called when a 'magento.account.invoice'
        # is created, it delay a job to export the invoice
        patched = 'openerp.addons.magentoerpconnect.invoice.export_invoice'
        # mock.patch prevents to create the job
        with mock.patch(patched) as export_invoice:
            self._invoice_open()
            assert len(self.invoice.magento_bind_ids) == 1
            export_invoice.delay.assert_called_with(
                mock.ANY,
                'magento.account.invoice',
                self.invoice.magento_bind_ids[0].id)

        # pay and verify it is NOT called
        # mock.patch prevents to create the job
        with mock.patch(patched) as export_invoice:
            self._pay_and_reconcile()
            self.assertEqual(self.invoice.state, 'paid')
            assert not export_invoice.delay.called

    def test_export_invoice_on_paid(self):
        """ Exporting an invoice: when it is paid """
        cr, uid = self.cr, self.uid
        store_ids = [store.id for website in self.backend.website_ids
                     for store in website.store_ids]
        # we setup the stores so they export the invoices as soon
        # as they are validated (open)
        self.registry('magento.store').write(
            cr, uid, store_ids, {'create_invoice_on': 'paid'})
        # this is the consumer called when a 'magento.account.invoice'
        # is created, it delay a job to export the invoice
        patched = 'openerp.addons.magentoerpconnect.invoice.export_invoice'
        # mock.patch prevents to create the job
        with mock.patch(patched) as export_invoice:
            self._invoice_open()
            assert not export_invoice.delay.called

        # pay and verify it is NOT called
        # mock.patch prevents to create the job
        with mock.patch(patched) as export_invoice:
            self._pay_and_reconcile()
            self.assertEqual(self.invoice.state, 'paid')
            assert len(self.invoice.magento_bind_ids) == 1
            export_invoice.delay.assert_called_with(
                mock.ANY, 'magento.account.invoice',
                self.invoice.magento_bind_ids[0].id)

    def test_export_invoice_on_payment_method_validate(self):
        """ Exporting an invoice: when it is validated with payment method """
        cr, uid = self.cr, self.uid
        store_ids = [store.id for website in self.backend.website_ids
                     for store in website.store_ids]
        # we setup the stores so they export the invoices as soon
        # as they are validated (open)
        self.registry('payment.method').write(
            cr, uid, self.payment_method_id, {'create_invoice_on': 'open'})
        # ensure we use the option of the payment method, not store
        self.registry('magento.store').write(
            cr, uid, store_ids, {'create_invoice_on': 'paid'})
        # this is the consumer called when a 'magento.account.invoice'
        # is created, it delay a job to export the invoice
        patched = 'openerp.addons.magentoerpconnect.invoice.export_invoice'
        # mock.patch prevents to create the job
        with mock.patch(patched) as export_invoice:
            self._invoice_open()

            assert len(self.invoice.magento_bind_ids) == 1
            export_invoice.delay.assert_called_with(
                mock.ANY, 'magento.account.invoice',
                self.invoice.magento_bind_ids[0].id)

        # pay and verify it is NOT called
        # mock.patch prevents to create the job
        with mock.patch(patched) as export_invoice:
            self._pay_and_reconcile()
            self.assertEqual(self.invoice.state, 'paid')
            assert not export_invoice.delay.called

    def test_export_invoice_on_payment_method_paid(self):
        """ Exporting an invoice: when it is paid on payment method """
        cr, uid = self.cr, self.uid
        store_ids = [store.id for website in self.backend.website_ids
                     for store in website.store_ids]
        # we setup the stores so they export the invoices as soon
        # as they are validated (open)
        self.registry('payment.method').write(
            cr, uid, self.payment_method_id, {'create_invoice_on': 'paid'})
        # ensure we use the option of the payment method, not store
        self.registry('magento.store').write(
            cr, uid, store_ids, {'create_invoice_on': 'open'})
        # this is the consumer called when a 'magento.account.invoice'
        # is created, it delay a job to export the invoice
        patched = 'openerp.addons.magentoerpconnect.invoice.export_invoice'
        # mock.patch prevents to create the job
        with mock.patch(patched) as export_invoice:
            self._invoice_open()
            assert not export_invoice.delay.called

        # pay and verify it is NOT called
        # mock.patch prevents to create the job
        with mock.patch(patched) as export_invoice:
            self._pay_and_reconcile()
            self.assertEqual(self.invoice.state, 'paid')
            assert len(self.invoice.magento_bind_ids) == 1
            export_invoice.delay.assert_called_with(
                mock.ANY, 'magento.account.invoice',
                self.invoice.magento_bind_ids[0].id)

    def _invoice_open(self):
        wf_service = netsvc.LocalService("workflow")
        wf_service.trg_validate(self.uid, 'account.invoice',
                                self.invoice.id, 'invoice_open', self.cr)
        self.invoice.refresh()

    def _pay_and_reconcile(self):
        self.invoice_model.pay_and_reconcile(
            self.cr, self.uid, [self.invoice.id],
            pay_amount=self.invoice.amount_total,
            pay_account_id=self.pay_account_id,
            period_id=self.period_id,
            pay_journal_id=self.journal_id,
            writeoff_acc_id=self.pay_account_id,
            writeoff_period_id=self.period_id,
            writeoff_journal_id=self.journal_id,
            name="Payment for tests of invoice's exports")
        self.invoice.refresh()

    @unittest2.skip("Needs to be implemented")
    def test_export_invoice_api(self):
        """ Exporting an invoice: call towards the Magento API """
