# Copyright 2014-2019 Camptocamp SA
# Copyright 2020 Opener B.V.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import json
from .common import Magento2SyncTestCase, recorder


class TestExportPicking(Magento2SyncTestCase):
    """ Test the export of pickings to Magento """

    def setUp(self):
        super(TestExportPicking, self).setUp()
        # import a sales order
        self.order_binding = self._import_record(
            'magento.sale.order', '12',
        )
        self.order_binding.ignore_exception = True
        # generate sale's picking
        self.order_binding.odoo_id.action_confirm()
        # Create inventory for add stock qty to lines
        # With this commit https://goo.gl/fRTLM3 the moves that where
        # force-assigned are not transferred in the picking
        for line in self.order_binding.odoo_id.order_line:
            if line.product_id.type == 'product':
                inventory = self.env['stock.inventory'].create({
                    'name': 'Inventory for line %s' % line.name,
                    'filter': 'product',
                    'product_id': line.product_id.id,
                    'line_ids': [(0, 0, {
                        'product_id': line.product_id.id,
                        'product_qty': line.product_uom_qty,
                        'location_id':
                        self.env.ref('stock.stock_location_stock').id
                    })]
                })
                inventory.action_validate()
        self.picking = self.order_binding.picking_ids
        self.assertEqual(len(self.picking), 1)
        magento_shop = self.picking.sale_id.magento_bind_ids[0].store_id
        magento_shop.send_picking_done_mail = True

    def test_export_complete_picking_trigger(self):
        """ Trigger export of a complete picking """
        self.picking.action_assign()
        with self.mock_with_delay() as (delayable_cls, delayable):
            # Deliver the entire picking, a 'magento.stock.picking'
            # should be created, then a job is generated that will export
            # the picking. Here the job is not created because we mock
            # 'with_delay()'
            self.env['stock.immediate.transfer'].create(
                {'pick_ids': [(4, self.picking.id)]}).process()
            self.assertEqual(self.picking.state, 'done')

            picking_binding = self.env['magento.stock.picking'].search(
                [('odoo_id', '=', self.picking.id),
                 ('backend_id', '=', self.backend.id)],
            )
            self.assertEqual(1, len(picking_binding))
            self.assertEqual('complete', picking_binding.picking_method)

            self.assertEqual(1, delayable_cls.call_count)
            delay_args, delay_kwargs = delayable_cls.call_args
            self.assertEqual((picking_binding,), delay_args)

            delayable.export_picking_done.assert_called_with(
                with_tracking=False
            )

    def test_export_complete_picking_job(self):
        """ Exporting a complete picking """
        self.picking.action_assign()
        with self.mock_with_delay():
            # Deliver the entire picking, a 'magento.stock.picking'
            # should be created, then a job is generated that will export
            # the picking. Here the job is not created because we mock
            # 'with_delay()'
            self.env['stock.immediate.transfer'].create(
                {'pick_ids': [(4, self.picking.id)]}).process()
            self.assertEqual(self.picking.state, 'done')
            picking_binding = self.env['magento.stock.picking'].search(
                [('odoo_id', '=', self.picking.id),
                 ('backend_id', '=', self.backend.id)],
            )
            self.assertEqual(1, len(picking_binding))

        with recorder.use_cassette(
                'test_export_picking_complete') as cassette:
            picking_binding.export_picking_done(with_tracking=False)

        self.assertEqual(1, len(cassette.requests))
        self.assertEqual(
            cassette.requests[0].uri,
            'http://magento/index.php/rest/V1/order/12/ship')
        self.assertDictEqual(
            json.loads(cassette.requests[0].body.decode('utf-8')),
            {"items": [
                {"order_item_id": "24", "qty": 1.0},
                {"order_item_id": "25", "qty": 1.0},
            ]})

        # Check that we have received and bound the magento ID
        self.assertEqual(picking_binding.external_id, '3')

    def test_export_partial_picking_trigger(self):
        """ Trigger export of a partial picking """
        # Prepare a partial picking
        # The sale order contains 2 lines with 1 product each
        self.picking.action_assign()
        self.picking.move_lines[0].quantity_done = 1
        self.picking.move_lines[1].quantity_done = 0
        # Remove reservation for line index 1
        self.picking.move_lines[1].move_line_ids.unlink()

        with self.mock_with_delay() as (delayable_cls, delayable):
            # Deliver the entire picking, a 'magento.stock.picking'
            # should be created, then a job is generated that will export
            # the picking. Here the job is not created because we mock
            # 'with_delay()'
            backorder_action = self.picking.button_validate()
            self.assertEqual(
                backorder_action['res_model'], 'stock.backorder.confirmation',
                'A backorder confirmation wizard action must be created')
            # Confirm backorder creation
            self.env['stock.backorder.confirmation'].browse(
                backorder_action['res_id']).process()

            self.assertEqual(self.picking.state, 'done')

            picking_binding = self.env['magento.stock.picking'].search(
                [('odoo_id', '=', self.picking.id),
                 ('backend_id', '=', self.backend.id)],
            )
            self.assertEqual(1, len(picking_binding))
            self.assertEqual('partial', picking_binding.picking_method)

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
        self.picking.action_assign()
        self.picking.move_lines[0].quantity_done = 1
        self.picking.move_lines[1].quantity_done = 0

        with self.mock_with_delay():
            # Deliver the entire picking, a 'magento.stock.picking'
            # should be created, then a job is generated that will export
            # the picking. Here the job is not created because we mock
            # 'with_delay()'
            self.env['stock.backorder.confirmation'].create(
                {'pick_ids': [(4, self.picking.id)]}).process()
            self.assertEqual(self.picking.state, 'done')

            picking_binding = self.env['magento.stock.picking'].search(
                [('odoo_id', '=', self.picking.id),
                 ('backend_id', '=', self.backend.id)],
            )
            self.assertEqual(1, len(picking_binding))

        with recorder.use_cassette(
                'test_export_picking_partial') as cassette:
            picking_binding.export_picking_done(with_tracking=False)

        self.assertEqual(
            cassette.requests[0].uri,
            'http://magento/index.php/rest/V1/order/12/ship')
        self.assertDictEqual(
            json.loads(cassette.requests[0].body.decode('utf-8')),
            {"items": [
                {"order_item_id": "24", "qty": 1.0},
            ]})

        # Check that we have received and bound the magento ID
        self.assertEqual(picking_binding.external_id, '5')

    def test_export_tracking_after_done_trigger(self):
        """ Trigger export of a tracking number """
        self.picking.action_assign()

        with self.mock_with_delay():
            self.env['stock.immediate.transfer'].create(
                {'pick_ids': [(4, self.picking.id)]}).process()
            self.assertEqual(self.picking.state, 'done')

        picking_binding = self.env['magento.stock.picking'].search(
            [('odoo_id', '=', self.picking.id),
             ('backend_id', '=', self.backend.id)],
        )
        self.assertEqual(1, len(picking_binding))

        with self.mock_with_delay() as (delayable_cls, delayable):
            self.picking.carrier_tracking_ref = 'XYZ'

            self.assertEqual(1, delayable_cls.call_count)
            delay_args, delay_kwargs = delayable_cls.call_args
            self.assertEqual((picking_binding,), delay_args)

            delayable.export_tracking_number.assert_called_with()

    def test_export_tracking_after_done_job(self):
        """ Job export of a tracking number """
        self.picking.action_assign()

        with self.mock_with_delay():
            self.env['stock.immediate.transfer'].create(
                {'pick_ids': [(4, self.picking.id)]}).process()
        self.assertEqual(self.picking.state, 'done')
        self.picking.carrier_tracking_ref = 'XYZ'
        self.order_binding.carrier_id.magento_tracking_title = 'Your shipment'

        picking_binding = self.env['magento.stock.picking'].search(
            [('odoo_id', '=', self.picking.id),
             ('backend_id', '=', self.backend.id)],
        )
        self.assertEqual(1, len(picking_binding))
        picking_binding.external_id = '3'

        with recorder.use_cassette(
                'test_export_tracking_number') as cassette:
            picking_binding.export_tracking_number()

        self.assertEqual(1, len(cassette.requests))
        self.assertEqual(
            cassette.requests[0].uri,
            'http://magento/index.php/rest/V1/shipment/track')
        self.assertEqual(
            json.loads(cassette.requests[0].body.decode('utf-8')),
            {'entity': {
                'order_id': '12',
                'parent_id': '3',
                'weight': 0,
                'qty': 1,
                'description': 'WH/OUT/00082',
                'track_number': 'XYZ',
                'title': 'Your shipment',
                'carrier_code': 'tablerate',
            }})
