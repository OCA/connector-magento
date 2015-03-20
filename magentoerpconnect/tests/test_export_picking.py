# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2015 Camptocamp SA
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

from openerp import _
from openerp.addons.magentoerpconnect.unit.import_synchronizer import (
    import_record)
from .common import (mock_api,
                     mock_job_delay_to_direct,
                     mock_urlopen_image,
                     SetUpMagentoSynchronized,
                     )
from .data_base import magento_base_responses


class TestExportPicking(SetUpMagentoSynchronized):
    """ Test the export of pickings to Magento """

    def setUp(self):
        super(TestExportPicking, self).setUp()
        binding_model = self.env['magento.sale.order']
        # import a sales order
        with mock_api(magento_base_responses):
            with mock_urlopen_image():
                import_record(self.session,
                              'magento.sale.order',
                              self.backend_id, 900000691)
        self.order_binding = binding_model.search(
            [('backend_id', '=', self.backend_id),
             ('magento_id', '=', '900000691'),
             ]
        )
        self.assertEquals(len(self.order_binding), 1)
        self.order_binding.ignore_exceptions = True
        # generate sale's picking
        self.order_binding.openerp_id.action_button_confirm()
        self.picking = self.order_binding.picking_ids
        self.assertEquals(len(self.picking), 1)
        magento_shop = self.picking.sale_id.magento_bind_ids[0].store_id
        magento_shop.send_picking_done_mail = True

    def test_export_complete_picking(self):
        """ Exporting a complete picking """
        self.picking.force_assign()
        job_path = ('openerp.addons.magentoerpconnect.'
                    'stock_picking.export_picking_done')
        response = {
            'sales_order_shipment.create': 987654321,
        }
        # mock 1. When '.delay()' is called on the job, call the function
        # directly instead.
        # mock 2. Replace the xmlrpc calls by a mock and return
        # 'response' values
        with mock_job_delay_to_direct(job_path), \
                mock_api(response, key_func=lambda m, a: m) as calls_done:
            # Deliver the entire picking, a 'magento.stock.picking'
            # should be created, then a job is generated that will export
            # the picking. Here it is forced to a direct call to Magento
            # (which is in fact the mock)
            self.picking.action_done()
            self.assertEquals(self.picking.state, 'done')

            # Here we check what call with which args has been done by the
            # BackendAdapter towards Magento
            self.assertEqual(len(calls_done), 1)
            method, (mag_order_id, items,
                     comment, email, include_comment) = calls_done[0]
            self.assertEqual(method, 'sales_order_shipment.create')
            self.assertEqual(mag_order_id, '900000691')
            # When the picking is complete, we send an empty dict
            self.assertEqual(items, {})
            self.assertEqual(comment, _("Shipping Created"))
            self.assertEqual(email, True)
            self.assertTrue(include_comment)

        # Check that we have received and bound the magento ID
        self.assertEquals(len(self.picking.magento_bind_ids), 1)
        binding = self.picking.magento_bind_ids
        self.assertEquals(binding.magento_id, '987654321')

    def test_export_partial_picking(self):
        """ Exporting a partial picking """
        # Prepare a partial picking
        # The sale order contains 2 lines with 1 product each
        self.picking.force_assign()
        self.picking.do_prepare_partial()
        self.picking.pack_operation_ids[0].product_qty = 1
        self.picking.pack_operation_ids[1].product_qty = 0

        job_path = ('openerp.addons.magentoerpconnect.'
                    'stock_picking.export_picking_done')
        response = {
            'sales_order_shipment.create': 987654321,
        }
        # mock 1. When '.delay()' is called on the job, call the function
        # directly instead.
        # mock 2. Replace the xmlrpc calls by a mock and return
        # 'response' values
        with mock_job_delay_to_direct(job_path), \
                mock_api(response, key_func=lambda m, a: m) as calls_done:
            # Deliver the partial picking, a 'magento.stock.picking'
            # should be created, then a job is generated that will export
            # the picking. Here it is forced to a direct call to Magento
            # (which is in fact the mock)
            self.picking.do_transfer()
            self.assertEquals(self.picking.state, 'done')

            # Here we check what call with which args has been done by the
            # BackendAdapter towards Magento
            self.assertEqual(len(calls_done), 1)
            method, (mag_order_id, items,
                     comment, email, include_comment) = calls_done[0]
            self.assertEqual(method, 'sales_order_shipment.create')
            self.assertEqual(mag_order_id, '900000691')
            # When the picking is partial, we have the details of the
            # delivered items
            self.assertEqual(items, {'1713': 1.0})
            self.assertEqual(comment, _("Shipping Created"))
            self.assertEqual(email, True)
            self.assertTrue(include_comment)

        # Check that we have received and bound the magento ID
        self.assertEquals(len(self.picking.magento_bind_ids), 1)
        binding = self.picking.magento_bind_ids
        self.assertEquals(binding.magento_id, '987654321')

        response = {
            'sales_order_shipment.create': 987654322,
        }
        backorder = self.picking.related_backorder_ids
        self.assertEquals(len(backorder), 1)
        # Deliver the rest in the remaining picking
        backorder.force_assign()
        # mock 1. When '.delay()' is called on the job, call the function
        # directly instead.
        # mock 2. Replace the xmlrpc calls by a mock and return
        # 'response' values
        with mock_job_delay_to_direct(job_path), \
                mock_api(response, key_func=lambda m, a: m) as calls_done:
            # call the direct export instead of 'delay()'
            backorder.action_done()
            self.assertEquals(self.picking.state, 'done')

            # Here we check what call with which args has been done by the
            # BackendAdapter towards Magento for the remaining picking
            self.assertEqual(len(calls_done), 1)
            method, (mag_order_id, items,
                     comment, email, include_comment) = calls_done[0]
            self.assertEqual(method, 'sales_order_shipment.create')
            self.assertEqual(mag_order_id, '900000691')
            self.assertEqual(items, {})
            self.assertEqual(comment, _("Shipping Created"))
            self.assertEqual(email, True)
            self.assertTrue(include_comment)

        self.assertEquals(len(backorder.magento_bind_ids), 1)
        self.assertEquals(backorder.magento_bind_ids.magento_id, '987654322')

    def test_export_tracking_after_done(self):
        """ A tracking number is exported after the picking is done """
        self.picking.force_assign()
        job_picking_path = ('openerp.addons.magentoerpconnect.'
                            'stock_picking.export_picking_done')
        job_tracking_path = ('openerp.addons.magentoerpconnect.'
                             'stock_tracking.export_tracking_number')
        response = {
            'sales_order_shipment.create': 987654321,
        }
        # mock 1. When '.delay()' is called on the job, call the function
        # directly instead.
        # mock 2. Replace the xmlrpc calls by a mock and return
        # 'response' values
        with mock_job_delay_to_direct(job_picking_path), \
                mock_api(response, key_func=lambda m, a: m) as calls_done:
            # Deliver the entire picking, a 'magento.stock.picking'
            # should be created, then a job is generated that will export
            # the picking. Here it is forced to a direct call to Magento
            # (which is in fact the mock)
            self.picking.action_done()
            self.assertEquals(self.picking.state, 'done')

        response = {
            'sales_order_shipment.addTrack': True,
            'sales_order_shipment.getCarriers': ['flatrate'],
        }
        with mock_job_delay_to_direct(job_tracking_path), \
                mock_api(response, key_func=lambda m, a: m) as calls_done:
            # set a tracking number
            self.picking.carrier_tracking_ref = 'XYZ'

            # Here we check what call with which args has been done by the
            # BackendAdapter towards Magento for the remaining picking
            self.assertEqual(len(calls_done), 2)

            # first call asks magento which carriers accept the tracking
            # numbers, normally magento does not support them on
            # flatrate, we lie for the sake of the test
            method, (mag_order_id,) = calls_done[0]
            self.assertEqual(method, 'sales_order_shipment.getCarriers')
            self.assertEqual(mag_order_id, '900000691')

            # the second call add the tracking number on magento
            method, (mag_shipment_id, carrier_code,
                     tracking_title, tracking_number) = calls_done[1]
            self.assertEqual(method, 'sales_order_shipment.addTrack')
            self.assertEqual(mag_shipment_id, '987654321')
            self.assertEqual(carrier_code, 'flatrate')
            self.assertEqual(tracking_title, '')
            self.assertEqual(tracking_number, 'XYZ')
