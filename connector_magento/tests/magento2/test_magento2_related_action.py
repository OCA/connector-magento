# Copyright 2014-2019 Camptocamp SA
# Copyright 2020 Opener B.V.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import mock

from .common import Magento2SyncTestCase
from odoo import exceptions


class TestRelatedActionStorage(Magento2SyncTestCase):
    """ Test related actions on stored jobs """

    def setUp(self):
        super(TestRelatedActionStorage, self).setUp()
        self.MagentoProduct = self.env['magento.product.product']
        self.QueueJob = self.env['queue.job']

    def test_unwrap_binding(self):
        """ Open a related action opening an unwrapped binding """
        product = self.env.ref('product.product_product_7')
        magento_product = self.MagentoProduct.create(
            {'odoo_id': product.id,
             'magento_internal_id': '1234356',
             'backend_id': self.backend.id})
        job = magento_product.with_delay().export_record()
        stored = job.db_record()

        expected = {
            'name': mock.ANY,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': product.id,
            'res_model': 'product.product',
        }
        self.assertEqual(stored.open_related_action(), expected)

    def test_link(self):
        """ Open a related action opening an url on Magento.
        It only succeeds if we already have the magento internal id. """
        self.backend.write({'admin_location': 'http://www.example.com/admin'})
        product = self.env.ref('product.product_product_7')
        job = self.MagentoProduct.with_delay().import_record(
            self.backend, product.default_code,
        )
        stored = job.db_record()
        with self.assertRaisesRegex(
                exceptions.UserError, 'import the product before'):
            stored.open_related_action()

        self.MagentoProduct.create(
            {'odoo_id': product.id,
             'external_id': product.default_code,
             'magento_internal_id': '1234356',
             'backend_id': self.backend.id})

        url = 'http://www.example.com/admin/catalog/product/edit/id/1234356'
        expected = {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': url,
        }
        self.assertEqual(stored.open_related_action(), expected)

    def test_link_no_location(self):
        """ Related action opening an url, admin location is not configured """
        self.backend.write({'admin_location': False})
        job = self.MagentoProduct.with_delay().import_record(
            self.backend, '123456'
        )
        stored = job.db_record()
        msg = r'No admin URL configured.*'
        with self.assertRaisesRegex(exceptions.UserError, msg):
            stored.open_related_action()
