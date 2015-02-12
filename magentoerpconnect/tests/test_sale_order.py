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
                     mock_urlopen_image)
from .test_data import magento_base_responses
from .test_synchronization import SetUpMagentoSynchronized
from ..sale import export_state_change

DB = common.DB
ADMIN_USER_ID = common.ADMIN_USER_ID


class TestSaleOrder(SetUpMagentoSynchronized):

    def _import_sale_order(self, increment_id):
        backend_id = self.backend_id
        with mock_api(magento_base_responses):
            with mock_urlopen_image():
                import_record(self.session,
                              'magento.sale.order',
                              backend_id, increment_id)
        MagentoOrder = self.registry('magento.sale.order')
        binding_ids = MagentoOrder.search(
            self.cr,
            self.uid,
            [('backend_id', '=', backend_id),
             ('magento_id', '=', str(increment_id))])
        self.assertEqual(len(binding_ids), 1)
        return MagentoOrder.browse(self.cr, self.uid, binding_ids[0])

    def test_copy_quotation(self):
        """ Copy a sales order with copy_quotation move bindings """
        binding = self._import_sale_order(900000691)
        order = binding.openerp_id
        SaleOrder = self.registry('sale.order')
        action = SaleOrder.copy_quotation(self.cr, self.uid, [order.id])
        new_id = action['res_id']
        order.refresh()
        self.assertFalse(order.magento_bind_ids)
        binding.refresh()
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
