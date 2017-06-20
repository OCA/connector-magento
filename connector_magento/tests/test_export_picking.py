# -*- coding: utf-8 -*-
# Copyright 2014-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from .common import MagentoSyncTestCase, recorder


class TestExportPicking(MagentoSyncTestCase):
    """ Test the export of pickings to Magento """

    def setUp(self):
        super(TestExportPicking, self).setUp()
        # import a sales order
        self.order_binding = self._import_record(
            'magento.sale.order', 100000201
        )
        self.order_binding.ignore_exception = True
        # generate sale's picking
        self.order_binding.odoo_id.action_confirm()
        self.picking = self.order_binding.picking_ids
        self.assertEquals(len(self.picking), 1)
        magento_shop = self.picking.sale_id.magento_bind_ids[0].store_id
        magento_shop.send_picking_done_mail = True

    def test_export_complete_picking_trigger(self):
        """ Trigger export of a complete picking """
        self.picking.force_assign()
        with self.mock_with_delay() as (delayable_cls, delayable):
            # Deliver the entire picking, a 'magento.stock.picking'
            # should be created, then a job is generated that will export
            # the picking. Here the job is not created because we mock
            # 'with_delay()'
            self.picking.do_transfer()
            self.assertEquals(self.picking.state, 'done')

            picking_binding = self.env['magento.stock.picking'].search(
                [('odoo_id', '=', self.picking.id),
                 ('backend_id', '=', self.backend.id)],
            )
            self.assertEquals(1, len(picking_binding))
            self.assertEquals('complete', picking_binding.picking_method)

            self.assertEqual(1, delayable_cls.call_count)
            delay_args, delay_kwargs = delayable_cls.call_args
            self.assertEqual((picking_binding,), delay_args)

            delayable.export_picking_done.assert_called_with(
                with_tracking=False
            )

    def test_export_complete_picking_job(self):
        """ Exporting a complete picking """
        self.picking.force_assign()
        with self.mock_with_delay():
            # Deliver the entire picking, a 'magento.stock.picking'
            # should be created, then a job is generated that will export
            # the picking. Here the job is not created because we mock
            # 'with_delay()'
            self.picking.do_transfer()
            self.assertEquals(self.picking.state, 'done')
            picking_binding = self.env['magento.stock.picking'].search(
                [('odoo_id', '=', self.picking.id),
                 ('backend_id', '=', self.backend.id)],
            )
            self.assertEquals(1, len(picking_binding))

        with recorder.use_cassette(
                'test_export_picking_complete') as cassette:
            picking_binding.export_picking_done(with_tracking=False)

        # 1. login, 2. sales_order_shipment.create,
        # 3. endSession
        self.assertEqual(3, len(cassette.requests))

        self.assertEqual(
            ('sales_order_shipment.create',
             ['100000201', {}, 'Shipping Created', True, True]),
            self.parse_cassette_request(cassette.requests[1].body)
        )

        # Check that we have received and bound the magento ID
        self.assertEquals(picking_binding.external_id, '987654321')

    def test_export_partial_picking_trigger(self):
        """ Trigger export of a partial picking """
        # Prepare a partial picking
        # The sale order contains 2 lines with 1 product each
        self.picking.force_assign()
        self.picking.do_prepare_partial()
        self.picking.pack_operation_ids[0].product_qty = 1
        self.picking.pack_operation_ids[1].product_qty = 0

        with self.mock_with_delay() as (delayable_cls, delayable):
            # Deliver the entire picking, a 'magento.stock.picking'
            # should be created, then a job is generated that will export
            # the picking. Here the job is not created because we mock
            # 'with_delay()'
            self.picking.do_transfer()
            self.assertEquals(self.picking.state, 'done')

            picking_binding = self.env['magento.stock.picking'].search(
                [('odoo_id', '=', self.picking.id),
                 ('backend_id', '=', self.backend.id)],
            )
            self.assertEquals(1, len(picking_binding))
            self.assertEquals('partial', picking_binding.picking_method)

            self.assertEqual(1, delayable_cls.call_count)
            delay_args, delay_kwargs = delayable_cls.call_args
            self.assertEqual((picking_binding,), delay_args)

            delayable.export_picking_done.assert_called_with(
                with_tracking=False
            )

    def test_export_partial_picking_job(self):
        """ Exporting a partial picking """
        # Prepare a partial picking
        # The sale order contains 2 lines with 1 product each
        self.picking.force_assign()
        self.picking.do_prepare_partial()
        self.picking.pack_operation_ids[0].product_qty = 1
        self.picking.pack_operation_ids[1].product_qty = 0

        with self.mock_with_delay():
            # Deliver the entire picking, a 'magento.stock.picking'
            # should be created, then a job is generated that will export
            # the picking. Here the job is not created because we mock
            # 'with_delay()'
            self.picking.do_transfer()
            self.assertEquals(self.picking.state, 'done')
            picking_binding = self.env['magento.stock.picking'].search(
                [('odoo_id', '=', self.picking.id),
                 ('backend_id', '=', self.backend.id)],
            )
            self.assertEquals(1, len(picking_binding))

        with recorder.use_cassette(
                'test_export_picking_partial') as cassette:
            picking_binding.export_picking_done(with_tracking=False)

        # 1. login, 2. sales_order_shipment.create,
        # 3. endSession
        self.assertEqual(3, len(cassette.requests))

        self.assertEqual(
            ('sales_order_shipment.create',
             ['100000201', {'543': 1.0}, 'Shipping Created', True, True]),
            self.parse_cassette_request(cassette.requests[1].body)
        )

        # Check that we have received and bound the magento ID
        self.assertEquals(picking_binding.external_id, '987654321')

    def test_export_tracking_after_done_trigger(self):
        """ Trigger export of a tracking number """
        self.picking.force_assign()

        with self.mock_with_delay():
            self.picking.do_transfer()
            self.assertEquals(self.picking.state, 'done')

        picking_binding = self.env['magento.stock.picking'].search(
            [('odoo_id', '=', self.picking.id),
             ('backend_id', '=', self.backend.id)],
        )
        self.assertEquals(1, len(picking_binding))

        with self.mock_with_delay() as (delayable_cls, delayable):
            self.picking.carrier_tracking_ref = 'XYZ'

            self.assertEqual(1, delayable_cls.call_count)
            delay_args, delay_kwargs = delayable_cls.call_args
            self.assertEqual((picking_binding,), delay_args)

            delayable.export_tracking_number.assert_called_with()

    def test_export_tracking_after_done_job(self):
        """ Job export of a tracking number """
        self.picking.force_assign()

        with self.mock_with_delay():
            self.picking.do_transfer()
            self.assertEquals(self.picking.state, 'done')
            self.picking.carrier_tracking_ref = 'XYZ'

        picking_binding = self.env['magento.stock.picking'].search(
            [('odoo_id', '=', self.picking.id),
             ('backend_id', '=', self.backend.id)],
        )
        self.assertEquals(1, len(picking_binding))
        picking_binding.external_id = '100000035'

        with recorder.use_cassette(
                'test_export_tracking_number') as cassette:
            picking_binding.export_tracking_number()

        # 1. login, 2. sales_order_shipment.getCarriers,
        # 3. sales_order_shipment.addTrack, 4. endSession
        self.assertEqual(4, len(cassette.requests))

        self.assertEqual(
            ('sales_order_shipment.getCarriers', ['100000201']),
            self.parse_cassette_request(cassette.requests[1].body)
        )

        self.assertEqual(
            ('sales_order_shipment.addTrack', ['100000035', 'ups', '', 'XYZ']),
            self.parse_cassette_request(cassette.requests[2].body)
        )
