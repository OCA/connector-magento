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

import mock

from openerp.addons.magentoerpconnect.unit.import_synchronizer import (
    import_record)
from .common import (mock_api,
                     mock_job_delay_to_direct,
                     mock_urlopen_image,
                     SetUpMagentoSynchronized,
                     )
from .data_base import magento_base_responses


class TestUpdateStockQty(SetUpMagentoSynchronized):
    """ Test the export of pickings to Magento """

    def _product_change_qty(self, product, new_qty):
        wizard_model = self.env['stock.change.product.qty']
        wizard = wizard_model.create({'product_id': product.id,
                                      'new_quantity': new_qty})
        wizard.change_product_qty()

    def setUp(self):
        super(TestUpdateStockQty, self).setUp()
        with mock_api(magento_base_responses):
            with mock_urlopen_image():
                import_record(self.session,
                              'magento.product.product',
                              self.backend_id, 16)
        product_model = self.env['magento.product.product']
        self.binding_product = product_model.search(
            [('backend_id', '=', self.backend_id),
             ('magento_id', '=', '16')])
        self.assertEqual(len(self.binding_product), 1)

    def test_compute_new_qty(self):
        product = self.binding_product.openerp_id
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
        patched = ('openerp.addons.magentoerpconnect.'
                   'product.export_product_inventory')
        with mock.patch(patched) as export_product_inventory:
            binding.recompute_magento_qty()
            self.assertEqual(binding.magento_qty, 30.0)
            export_product_inventory.delay.assert_called_with(
                mock.ANY,
                'magento.product.product',
                binding.id,
                priority=20,
                fields=['magento_qty'])

    def test_compute_new_qty_different_field(self):
        stock_field = self.env.ref('stock.field_product_product_qty_available')
        self.backend.product_stock_field_id = stock_field
        product = self.binding_product.openerp_id
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
        outgoing.action_confirm()
        outgoing.action_assign()

        # the virtual is now 19, available still 30
        self.assertEqual(product.qty_available, 30.0)
        self.assertEqual(product.virtual_available, 19.0)
        self.assertEqual(binding.magento_qty, 0.0)

        # search for the new quantities to push to Magento
        # we mock the job so we can check it .delay() is called on it
        # when the quantity is changed
        patched = ('openerp.addons.magentoerpconnect.'
                   'product.export_product_inventory')
        with mock.patch(patched) as export_product_inventory:
            binding.recompute_magento_qty()
            # since we have chose to use the field qty_available on the
            # backend, we should have 30
            self.assertEqual(binding.magento_qty, 30.0)
            export_product_inventory.delay.assert_called_with(
                mock.ANY,
                'magento.product.product',
                binding.id,
                priority=20,
                fields=['magento_qty'])

    def test_export_qty_api(self):
        product = self.binding_product.openerp_id
        binding = self.binding_product

        job_path = ('openerp.addons.magentoerpconnect.'
                    'product.export_product_inventory')
        response = {
            'oerp_cataloginventory_stock_item.update': True,
        }

        self._product_change_qty(product, 30)
        # mock 1. When '.delay()' is called on the job, call the function
        # directly instead.
        # mock 2. Replace the xmlrpc calls by a mock and return
        # 'response' values
        with mock_job_delay_to_direct(job_path), \
                mock_api(response, key_func=lambda m, a: m) as calls_done:
            binding.recompute_magento_qty()

            # Here we check what call with which args has been done by the
            # BackendAdapter towards Magento to export the new stock
            # values
            self.assertEqual(len(calls_done), 1)
            method, (product_id, stock_data) = calls_done[0]
            self.assertEqual(method, 'oerp_cataloginventory_stock_item.update')
            self.assertEqual(product_id, 16)
            self.assertEqual(stock_data, {'qty': 30.0, 'is_in_stock': 1})

    def test_export_qty_api_on_write(self):

        job_path = ('openerp.addons.magentoerpconnect.'
                    'product.export_product_inventory')
        response = {
            'oerp_cataloginventory_stock_item.update': True,
        }

        # mock 1. When '.delay()' is called on the job, call the function
        # directly instead.
        # mock 2. Replace the xmlrpc calls by a mock and return
        # 'response' values
        with mock_job_delay_to_direct(job_path), \
                mock_api(response, key_func=lambda m, a: m) as calls_done:
            self.binding_product.write({
                'magento_qty': 333,
                'backorders': 'yes-and-notification',
                'manage_stock': 'yes',
            })

            # Here we check what call with which args has been done by the
            # BackendAdapter towards Magento to export the new stock
            # values
            self.assertEqual(len(calls_done), 1)
            method, (product_id, stock_data) = calls_done[0]
            self.assertEqual(method, 'oerp_cataloginventory_stock_item.update')
            self.assertEqual(product_id, 16)
            self.assertEqual(stock_data, {'qty': 333.0,
                                          'is_in_stock': 1,
                                          'manage_stock': 1,
                                          'use_config_manage_stock': 0,
                                          'backorders': 2,
                                          'use_config_backorders': 0,
                                          })
