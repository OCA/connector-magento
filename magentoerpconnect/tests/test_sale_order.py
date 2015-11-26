# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2014 Camptocamp SA
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
from openerp.addons.magentoerpconnect.unit.import_synchronizer import (
    import_record)
import openerp.tests.common as common
from .common import (mock_api,
                     mock_urlopen_image,
                     SetUpMagentoSynchronized,
                     )
from .data_base import magento_base_responses
from .data_guest_order import guest_order_responses
from ..sale import export_state_change

DB = common.DB
ADMIN_USER_ID = common.ADMIN_USER_ID


class TestSaleOrder(SetUpMagentoSynchronized):

    def _import_sale_order(self, increment_id, responses=None):
        if responses is None:
            responses = magento_base_responses
        backend_id = self.backend_id
        with mock_api(responses):
            with mock_urlopen_image():
                import_record(self.session,
                              'magento.sale.order',
                              backend_id, increment_id)
        MagentoOrder = self.env['magento.sale.order']
        binding = MagentoOrder.search(
            [('backend_id', '=', backend_id),
             ('magento_id', '=', str(increment_id))]
        )
        self.assertEqual(len(binding), 1)
        return binding

    def test_import_options(self):
        """Test import options such as the account_analytic_account and
        the fiscal_position that can be specified at different level of the
        backend models (backend, wesite, store and storeview)
        """
        binding = self._import_sale_order(900000691)
        self.assertFalse(binding.project_id)
        self.assertFalse(binding.fiscal_position)
        # keep a reference to backend models the website
        storeview_id = binding.storeview_id
        store_id = storeview_id.store_id
        website_id = store_id.website_id
        binding.openerp_id.unlink()
        binding.unlink()
        # define options at the backend level
        fp1 = self.env['account.fiscal.position'].create({'name': "fp1"})
        account_analytic_id = self.env['account.analytic.account'].create(
            {'name': 'aaa1'})
        self.backend.account_analytic_id = account_analytic_id
        self.backend.fiscal_position_id = fp1.id
        binding = self._import_sale_order(900000691)
        self.assertEquals(binding.project_id, account_analytic_id)
        self.assertEquals(binding.fiscal_position, fp1)
        binding.openerp_id.unlink()
        binding.unlink()
        # define options at the website level
        account_analytic_id = self.env['account.analytic.account'].create(
            {'name': 'aaa2'})
        fp2 = self.env['account.fiscal.position'].create({'name': "fp2"})
        website_id.specific_account_analytic_id = account_analytic_id
        website_id.specific_fiscal_position_id = fp2.id
        binding = self._import_sale_order(900000691)
        self.assertEquals(binding.project_id, account_analytic_id)
        self.assertEquals(binding.fiscal_position, fp2)
        binding.openerp_id.unlink()
        binding.unlink()
        # define options at the store level
        account_analytic_id = self.env['account.analytic.account'].create(
            {'name': 'aaa3'})
        fp3 = self.env['account.fiscal.position'].create({'name': "fp3"})
        store_id.specific_account_analytic_id = account_analytic_id
        store_id.specific_fiscal_position_id = fp3.id
        binding = self._import_sale_order(900000691)
        self.assertEquals(binding.project_id, account_analytic_id)
        self.assertEquals(binding.fiscal_position, fp3)
        binding.openerp_id.unlink()
        binding.unlink()
        # define options at the storeview level
        account_analytic_id = self.env['account.analytic.account'].create(
            {'name': 'aaa4'})
        fp4 = self.env['account.fiscal.position'].create({'name': "fp4"})
        storeview_id.specific_account_analytic_id = account_analytic_id
        storeview_id.specific_fiscal_position_id = fp4.id
        binding = self._import_sale_order(900000691)
        self.assertEquals(binding.project_id, account_analytic_id)
        self.assertEquals(binding.fiscal_position, fp4)

    def test_copy_quotation(self):
        """ Copy a sales order with copy_quotation move bindings """
        binding = self._import_sale_order(900000691)
        order = binding.openerp_id
        action = order.copy_quotation()
        new_id = action['res_id']
        self.assertFalse(order.magento_bind_ids)
        self.assertEqual(binding.openerp_id.id, new_id)
        for mag_line in binding.magento_order_line_ids:
            self.assertEqual(mag_line.order_id.id, new_id)

    def test_cancel_delay_job(self):
        """ Cancel an order, delay a cancel job """
        binding = self._import_sale_order(900000691)
        order = binding.openerp_id
        patched = 'openerp.addons.magentoerpconnect.sale.export_state_change'
        # patch the job so it won't be created and we will be able
        # to check if it is called
        with mock.patch(patched) as mock_export_state_change:
            order.action_cancel()
            called = mock_export_state_change.delay
            called.assert_called_with(mock.ANY,
                                      'magento.sale.order',
                                      binding.id,
                                      allowed_states=['cancel'],
                                      description=mock.ANY)

    def test_cancel_export(self):
        """ Export the cancel state """
        binding = self._import_sale_order(900000691)
        order = binding.openerp_id
        # patch the job so it won't be created
        patched = 'openerp.addons.magentoerpconnect.sale.export_state_change'
        with mock.patch(patched):
            order.action_cancel()
        response = {
            'sales_order.info': {'status': 'new'},
            'sales_order.addComment': True,
        }
        with mock_api(response,
                      key_func=lambda method, args: method) as calls_done:
            # call the job synchronously, so we check the calls
            export_state_change(self.session, 'magento.sale.order',
                                binding.id, allowed_states=['cancel'])

            # call 1: sales_order.info to read the status
            # call 2: sales_order.addComment to add a status comment
            self.assertEqual(len(calls_done), 2)
            method, (magento_id, state) = calls_done[1]
            self.assertEqual(method, 'sales_order.addComment')
            self.assertEqual(magento_id, binding.magento_id)
            self.assertEqual(state, 'canceled')

    def test_copy_quotation_delay_export_state(self):
        """ Delay a state export on new copy from canceled order """
        binding = self._import_sale_order(900000691)
        order = binding.openerp_id

        # cancel the order
        patched = 'openerp.addons.magentoerpconnect.sale.export_state_change'
        with mock.patch(patched):
            # cancel the sales order, a job exporting the cancel status
            # to Magento is normally created (muted here)
            order.action_cancel()

        SaleOrder = self.registry('sale.order')
        patched = 'openerp.addons.magentoerpconnect.sale.export_state_change'
        with mock.patch(patched) as mock_export_state_change:
            # create a copy of quotation, the new order should be linked to
            # the Magento sales order
            action = SaleOrder.copy_quotation(self.cr, self.uid, [order.id])
            new_id = action['res_id']
            binding.refresh()
            order = binding.openerp_id
            self.assertEqual(order.id, new_id)

            called = mock_export_state_change.delay
            called.assert_called_with(mock.ANY,
                                      'magento.sale.order',
                                      binding.id,
                                      description=mock.ANY)

    def test_copy_quotation_export_state(self):
        """ Export a new state on new copy from canceled order """
        binding = self._import_sale_order(900000691)
        order = binding.openerp_id
        SaleOrder = self.registry('sale.order')

        # cancel the order
        patched = 'openerp.addons.magentoerpconnect.sale.export_state_change'
        with mock.patch(patched):
            # cancel the sales order, a job exporting the cancel status
            # to Magento is normally created (muted here)
            order.action_cancel()

            # create a copy of quotation, the new order should be linked to
            # the Magento sales order
            action = SaleOrder.copy_quotation(self.cr, self.uid, [order.id])
            new_id = action['res_id']
            binding.refresh()
            order = binding.openerp_id
            self.assertEqual(order.id, new_id)

        # we will check if the correct messages are sent to Magento
        response = {
            'sales_order.info': {'status': 'canceled'},
            'sales_order.addComment': True,
        }
        with mock_api(response,
                      key_func=lambda method, args: method) as calls_done:
            # call the job synchronously, so we check the calls
            export_state_change(self.session, 'magento.sale.order',
                                binding.id)

            # call 1: sales_order.info to read the status
            # call 2: sales_order.addComment to add a status comment
            self.assertEqual(len(calls_done), 2)
            method, (magento_id, state) = calls_done[1]
            self.assertEqual(method, 'sales_order.addComment')
            self.assertEqual(magento_id, binding.magento_id)
            self.assertEqual(state, 'pending')

    def test_import_edited(self):
        """ Import of an edited sale order links to its parent """
        binding = self._import_sale_order(900000691)
        new_binding = self._import_sale_order('900000691-1')
        self.assertEqual(new_binding.magento_parent_id, binding)
        self.assertTrue(binding.canceled_in_backend)

    def test_import_storeview_options(self):
        """ Check if storeview options are propagated """
        storeview = self.env['magento.storeview'].search([
            ('backend_id', '=', self.backend_id),
            ('magento_id', '=', '1')
        ])
        team = self.env['crm.case.section'].create({'name': 'Magento Team'})
        storeview.section_id = team
        binding = self._import_sale_order(900000691)
        self.assertEqual(binding.section_id, team)

    def test_import_guest_order(self):
        binding = self._import_sale_order(900000700,
                                          responses=[magento_base_responses,
                                                     guest_order_responses])
        partner_binding = binding.partner_id.magento_bind_ids
        self.assertEqual(partner_binding.magento_id, 'guestorder:900000700')
        self.assertTrue(partner_binding.guest_customer)

    def test_import_carrier_product(self):
        """ Product of a carrier is used in the sale line """
        product = self.env['product.product'].create({
            'name': 'Carrier Product',
        })
        self.env['delivery.carrier'].create({
            'name': 'Flatrate',
            'partner_id': self.env.ref('base.main_partner').id,
            'product_id': product.id,
            'magento_code': 'flatrate_flatrate',
            'magento_carrier_code': 'flatrate_flatrate',
        })
        binding = self._import_sale_order(900000691)
        # check if we have a line with the carrier product,
        # which is the shipping line
        shipping_line = False
        for line in binding.order_line:
            if line.product_id == product:
                shipping_line = True
        self.assertTrue(shipping_line,
                        msg='No shipping line with the product of the carrier '
                            'has been found. Line names: %s' %
                            (', '.join("%s (%s)" % (line.name,
                                                    line.product_id.name)
                                       for line
                                       in binding.order_line),))
