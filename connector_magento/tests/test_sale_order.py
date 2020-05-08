# Copyright 2014-2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from collections import namedtuple
from .common import MagentoSyncTestCase, recorder

ExpectedOrderLine = namedtuple(
    'ExpectedOrderLine',
    'product_id name price_unit product_uom_qty'
)


class TestSaleOrder(MagentoSyncTestCase):

    def setUp(self):
        super(TestSaleOrder, self).setUp()

    def _import_sale_order(self, increment_id, cassette=True):
        return self._import_record('magento.sale.order',
                                   increment_id, cassette=cassette)

    def test_import_sale_order(self):
        """ Import sale order: check """
        binding = self._import_sale_order(100000201)
        self.assertEqual(binding.workflow_process_id, self.workflow,
                         "If the automatic workflow is empty, the "
                         "onchanges have not been applied.")

    def test_import_sale_order_with_prefix(self):
        """ Import sale order with prefix """
        self.backend.write({'sale_prefix': 'EC'})
        binding = self._import_sale_order(100000201)
        self.assertEqual(binding.name, 'EC100000201')

    def test_import_sale_order_with_configurable(self):
        """ Import sale order with configurable product """
        binding = self._import_sale_order(100000201)

        prod1 = self.env['magento.product.product'].search(
            [('external_id', '=', 512), ('backend_id', '=', self.backend.id)]
        )
        prod2 = self.env['magento.product.product'].search(
            [('external_id', '=', 302), ('backend_id', '=', self.backend.id)]
        )
        ship = binding.carrier_id.product_id
        expected = [
            ExpectedOrderLine(
                product_id=prod1.odoo_id,
                name='Tori Tank',
                price_unit=60.,
                product_uom_qty=2.,
            ),
            ExpectedOrderLine(
                product_id=prod2.odoo_id,
                name='Racer Back Maxi Dress',
                price_unit=224.,
                product_uom_qty=1.,
            ),
            ExpectedOrderLine(
                product_id=ship,
                name='Shipping Costs',
                price_unit=12.31,
                product_uom_qty=1.,
            ),
        ]

        self.assert_records(expected, binding.order_line)

    def test_import_sale_order_copy_quotation(self):
        """ Copy a sales order with copy_quotation move bindings """
        binding = self._import_sale_order(100000201)
        order = binding.odoo_id
        order.action_cancel()
        new = order.copy()
        self.assertFalse(order.magento_bind_ids)
        self.assertEqual(binding.odoo_id, new)
        for mag_line in binding.magento_order_line_ids:
            self.assertEqual(mag_line.order_id, new)

    def test_import_sale_order_edited(self):
        """ Import of an edited sale order links to its parent """
        with recorder.use_cassette('import_sale_order_edited_1'):
            binding = self._import_sale_order(100000200, cassette=False)
        with recorder.use_cassette('import_sale_order_edited_2'):
            new_binding = self._import_sale_order('100000200-1',
                                                  cassette=False)
        self.assertEqual(new_binding.magento_parent_id, binding)
        self.assertTrue(binding.canceled_in_backend)

    def test_import_sale_order_storeview_options(self):
        """ Check if storeview options are propagated """
        storeview = self.env['magento.storeview'].search([
            ('backend_id', '=', self.backend.id),
            ('external_id', '=', '1')
        ])
        team = self.env['crm.team'].create({'name': 'Magento Team'})
        storeview.team_id = team
        binding = self._import_sale_order(100000201)
        self.assertEqual(binding.team_id, team)

    def test_import_sale_order_guest(self):
        binding = self._import_sale_order(145000008)
        partner_binding = binding.partner_id.magento_bind_ids
        self.assertEqual(partner_binding.external_id, 'guestorder:145000008')
        self.assertTrue(partner_binding.guest_customer)

    def test_import_sale_order_carrier_product(self):
        """ Product of a carrier is used in the sale line """
        product = self.env['product.product'].create({
            'name': 'Carrier Product',
        })
        self.env['delivery.carrier'].create({
            'name': 'ups_GND',
            'product_id': product.id,
            'magento_code': 'ups_GND',
            'magento_carrier_code': 'ups_GND',
        })
        binding = self._import_sale_order(100000201)
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

    def test_import_sale_order_options(self):
        """Test import options such as the account_analytic_account and
        the fiscal_position that can be specified at different level of the
        backend models (backend, website, store and storeview)
        """
        binding = self._import_sale_order(100000201)
        self.assertFalse(binding.analytic_account_id)
        default_fp = self.env['account.fiscal.position'].get_fiscal_position(
            binding.partner_id.id, binding.partner_shipping_id.id)
        self.assertEqual(binding.fiscal_position_id.id, default_fp)
        # keep a reference to backend models the website
        storeview_id = binding.storeview_id
        store_id = storeview_id.store_id
        website_id = store_id.website_id
        binding.odoo_id.unlink()
        binding.unlink()
        # define options at the backend level
        fp1 = self.env['account.fiscal.position'].create({'name': "fp1"})
        account_analytic_id = self.env['account.analytic.account'].create(
            {'name': 'aaa1'})
        self.backend.account_analytic_id = account_analytic_id
        self.backend.fiscal_position_id = fp1.id
        binding = self._import_sale_order(100000201)
        self.assertEqual(binding.analytic_account_id, account_analytic_id)
        self.assertEqual(binding.fiscal_position_id, fp1)
        binding.odoo_id.unlink()
        binding.unlink()
        # define options at the website level
        account_analytic_id = self.env['account.analytic.account'].create(
            {'name': 'aaa2'})
        fp2 = self.env['account.fiscal.position'].create({'name': "fp2"})
        website_id.specific_account_analytic_id = account_analytic_id
        website_id.specific_fiscal_position_id = fp2.id
        binding = self._import_sale_order(100000201)
        self.assertEqual(binding.analytic_account_id, account_analytic_id)
        self.assertEqual(binding.fiscal_position_id, fp2)
        binding.odoo_id.unlink()
        binding.unlink()
        # define options at the store level
        account_analytic_id = self.env['account.analytic.account'].create(
            {'name': 'aaa3'})
        fp3 = self.env['account.fiscal.position'].create({'name': "fp3"})
        store_id.specific_account_analytic_id = account_analytic_id
        store_id.specific_fiscal_position_id = fp3.id
        binding = self._import_sale_order(100000201)
        self.assertEqual(binding.analytic_account_id, account_analytic_id)
        self.assertEqual(binding.fiscal_position_id, fp3)
        binding.odoo_id.unlink()
        binding.unlink()
        # define options at the storeview level
        account_analytic_id = self.env['account.analytic.account'].create(
            {'name': 'aaa4'})
        fp4 = self.env['account.fiscal.position'].create({'name': "fp4"})
        storeview_id.specific_account_analytic_id = account_analytic_id
        storeview_id.specific_fiscal_position_id = fp4.id
        binding = self._import_sale_order(100000201)
        self.assertEqual(binding.analytic_account_id, account_analytic_id)
        self.assertEqual(binding.fiscal_position_id, fp4)

    def test_sale_order_cancel_delay_job(self):
        """ Cancel an order, delay a cancel job """
        binding = self._import_sale_order(100000201)
        with self.mock_with_delay() as (delayable_cls, delayable):
            order = binding.odoo_id

            order.action_cancel()
            self.assertEqual(1, delayable_cls.call_count)
            delay_args, __ = delayable_cls.call_args
            self.assertEqual(binding, delay_args[0])

            delayable.export_state_change.assert_called_with(
                allowed_states=['cancel'],
            )

    def test_cancel_export(self):
        """ Export the cancel state """
        binding = self._import_sale_order(100000201)
        with self.mock_with_delay():
            order = binding.odoo_id
            order.action_cancel()

        with recorder.use_cassette(
                'test_sale_order_cancel_export') as cassette:

            # call the job synchronously, so we check the calls
            binding.export_state_change(allowed_states=['cancel'])
            # 1. login, 2. sales_order.info,
            # 3. sales_order.addComment, 4. endSession
            self.assertEqual(4, len(cassette.requests))

            self.assertEqual(
                ('sales_order.info', ['100000201']),
                self.parse_cassette_request(cassette.requests[1].body)
            )
            self.assertEqual(
                ('sales_order.addComment', ['100000201', 'canceled']),
                self.parse_cassette_request(cassette.requests[2].body)
            )

    def test_copy_quotation_delay_export_state(self):
        """ Delay a state export on new copy from canceled order """
        with recorder.use_cassette('import_sale_order_edited_1'):
            binding = self._import_sale_order(100000200, cassette=False)

        order = binding.odoo_id

        # cancel the order
        with self.mock_with_delay():
            order = binding.odoo_id
            order.action_cancel()

        with self.mock_with_delay() as (delayable_cls, delayable):
            # create a copy of quotation, the new order should be linked to
            # the Magento sales order
            new = order.copy()
            order = binding.odoo_id
            self.assertEqual(order, new)

            self.assertEqual(1, delayable_cls.call_count)
            delay_args, __ = delayable_cls.call_args
            self.assertEqual(binding, delay_args[0])

            self.assertTrue(delayable.export_state_change.called)

    def test_copy_quotation_export_state(self):
        """ Export a new state on new copy from canceled order """
        with recorder.use_cassette('import_sale_order_edited_1'):
            binding = self._import_sale_order(100000200, cassette=False)

        # cancel the order
        with self.mock_with_delay():
            order = binding.odoo_id
            order.action_cancel()
            order = order.copy()

        with recorder.use_cassette(
                'test_sale_order_reopen_export') as cassette:

            # call the job synchronously, so we check the calls
            binding.export_state_change()
            # 1. login, 2. sales_order.info,
            # 3. sales_order.addComment, 4. endSession
            self.assertEqual(4, len(cassette.requests))

            self.assertEqual(
                ('sales_order.info', ['100000200']),
                self.parse_cassette_request(cassette.requests[1].body)
            )
            self.assertEqual(
                ('sales_order.addComment', ['100000200', 'pending']),
                self.parse_cassette_request(cassette.requests[2].body)
            )
