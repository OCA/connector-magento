# Copyright 2015-2019 Camptocamp SA
# Copyright 2020 Opener B.V.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import json
from .common import Magento2SyncTestCase, recorder


class TestUpdateStockQty(Magento2SyncTestCase):
    """ Test the export of pickings to Magento """

    def _product_change_qty(self, product, new_qty, location_id=False):
        wizard_model = self.env['stock.change.product.qty']
        data = {'product_id': product.id,
                'new_quantity': new_qty}
        if location_id:
            data['location_id'] = location_id
        wizard = wizard_model.create(data)
        wizard.change_product_qty()

    def setUp(self):
        super(TestUpdateStockQty, self).setUp()
        self.binding_product = self._import_record(
            'magento.product.product', 'MH09-L-Blue',
        )

    def test_compute_new_qty(self):
        product = self.binding_product.odoo_id
        binding = self.binding_product
        # start with 0
        self.assertEqual(product.virtual_available, 0.0)
        self.assertEqual(binding.magento_qty, 0.0)

        # change to 30
        self._product_change_qty(product, 30)

        # the virtual available is 30, the magento qty has not been
        # updated yet
        self.assertEqual(product.virtual_available, 30.0)
        self.assertEqual(binding.magento_qty, 0.0)

        # search for the new quantities to push to Magento
        # we mock the job so we can check it .delay() is called on it
        # when the quantity is changed
        with self.mock_with_delay() as (delayable_cls, delayable):
            binding.recompute_magento_qty()
            self.assertEqual(binding.magento_qty, 30.0)

            self.assertEqual(1, delayable_cls.call_count)
            delay_args, delay_kwargs = delayable_cls.call_args
            self.assertEqual((binding,), delay_args)
            self.assertEqual(20, delay_kwargs.get('priority'))

            delayable.export_inventory.assert_called_with(
                fields=['magento_qty'],
            )

    def test_compute_new_qty_different_field(self):
        stock_field = self.env.ref(
            'stock.field_product_product__qty_available')
        self.backend.product_stock_field_id = stock_field
        product = self.binding_product.odoo_id
        binding = self.binding_product
        # start with 0
        self.assertEqual(product.qty_available, 0.0)
        self.assertEqual(product.virtual_available, 0.0)
        self.assertEqual(binding.magento_qty, 0.0)

        # change to 30
        self._product_change_qty(product, 30)

        # the virtual available is 30, the magento qty has not been
        # updated yet
        self.assertEqual(product.qty_available, 30.0)
        self.assertEqual(product.virtual_available, 30.0)
        self.assertEqual(binding.magento_qty, 0.0)

        # create an outgoing move
        customer_location = self.env.ref('stock.stock_location_customers')
        outgoing = self.env['stock.move'].create({
            'name': product.name,
            'product_id': product.id,
            'product_uom_qty': 11,
            'product_uom': product.uom_id.id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'location_dest_id': customer_location.id,
        })
        outgoing._action_confirm()
        outgoing._action_assign()

        # the virtual is now 19, available still 30
        self.assertEqual(product.qty_available, 30.0)
        self.assertEqual(product.virtual_available, 19.0)
        self.assertEqual(binding.magento_qty, 0.0)

        # search for the new quantities to push to Magento
        # we mock the job so we can check it .delay() is called on it
        # when the quantity is changed
        with self.mock_with_delay() as (delayable_cls, delayable):
            binding.recompute_magento_qty()
            # since we have chose to use the field qty_available on the
            # backend, we should have 30
            self.assertEqual(binding.magento_qty, 30.0)

            self.assertEqual(1, delayable_cls.call_count)
            delay_args, delay_kwargs = delayable_cls.call_args
            self.assertEqual((binding,), delay_args)
            self.assertEqual(20, delay_kwargs.get('priority'))

            delayable.export_inventory.assert_called_with(
                fields=['magento_qty'],
            )

    def test_export_qty_api(self):
        product = self.binding_product.odoo_id
        binding = self.binding_product

        self._product_change_qty(product, 30)
        with self.mock_with_delay():  # disable job
            binding.recompute_magento_qty()

        with recorder.use_cassette(
                'test_product_export_qty') as cassette:
            # call the job directly
            binding.export_inventory(fields=['magento_qty'])

            self.assertEqual(2, len(cassette.requests))
            self.assertEqual(
                json.loads(cassette.requests[1].body.decode('utf-8')),
                {"stockItem": {"qty": 30.0, "is_in_stock": 1}})

    def test_export_product_inventory_write(self):
        with self.mock_with_delay() as (delayable_cls, delayable):
            self.binding_product.write({
                'magento_qty': 333,
                'backorders': 'yes-and-notification',
                'manage_stock': 'yes',
            })

            self.assertEqual(1, delayable_cls.call_count)
            delay_args, delay_kwargs = delayable_cls.call_args
            self.assertEqual((self.binding_product,), delay_args)
            self.assertEqual(20, delay_kwargs.get('priority'))

            cargs, ckwargs = delayable.export_inventory.call_args
            self.assertFalse(cargs)
            self.assertEqual(set(ckwargs.keys()), set(['fields']))
            self.assertEqual(
                set(ckwargs['fields']), set([
                    'manage_stock', 'backorders', 'magento_qty']))

    def test_export_product_inventory_write_job(self):
        with self.mock_with_delay():
            self.binding_product.write({
                'magento_qty': 333,
                'backorders': 'yes-and-notification',
                'manage_stock': 'yes',
            })

        with recorder.use_cassette(
                'test_product_export_qty_config') as cassette:
            self.binding_product.export_inventory(
                fields=['backorders', 'magento_qty', 'manage_stock']
            )

            # 1. Get stockItems
            # 2. Put stockItem for default location
            self.assertEqual(2, len(cassette.requests))

            # Here we check what call with which args has been done by the
            # BackendAdapter towards Magento to export the new stock
            # values
            self.assertEqual(
                json.loads(cassette.requests[1].body.decode('utf-8')),
                {"stockItem": {
                    'qty': 333.,
                    'is_in_stock': 1,
                    'manage_stock': 1,
                    'use_config_manage_stock': 0,
                    'backorders': 2,
                    'use_config_backorders': 0,
                }})

    def test_compute_new_qty_with_location(self):
        product = self.binding_product.odoo_id
        binding = self.binding_product
        # start with 0
        self.assertEqual(product.virtual_available, 0.0)
        self.assertEqual(binding.magento_qty, 0.0)

        my_location_id = self.env.ref("stock.stock_location_components").id
        binding = binding.with_context(location=my_location_id)

        # change to 30
        self._product_change_qty(product, 30)
        self._product_change_qty(product, 5, my_location_id)

        # the virtual available is 30, the magento qty has not been
        # updated yet
        self.assertEqual(product.virtual_available, 35.0)
        self.assertEqual(binding.magento_qty, 0.0)

        # search for the new quantities to push to Magento
        # we mock the job so we can check it .delay() is called on it
        # when the quantity is changed
        with self.mock_with_delay() as (delayable_cls, delayable):
            binding.recompute_magento_qty()
            self.assertEqual(binding.magento_qty, 5.0)

            self.assertEqual(1, delayable_cls.call_count)
            delay_args, delay_kwargs = delayable_cls.call_args
            self.assertEqual((binding,), delay_args)
            self.assertEqual(20, delay_kwargs.get('priority'))

            delayable.export_inventory.assert_called_with(
                fields=['magento_qty'],
            )
