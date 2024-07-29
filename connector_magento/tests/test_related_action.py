# Copyright 2014-2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import mock

from .common import MagentoSyncTestCase
from odoo import exceptions


class TestRelatedActionStorage(MagentoSyncTestCase):
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
        """ Open a related action opening an url on Magento """
        self.backend.write({'admin_location': 'http://www.example.com/admin'})
        job = self.MagentoProduct.with_delay().import_record(
            self.backend, '123456'
        )
        stored = job.db_record()

        url = 'http://www.example.com/admin/catalog_product/edit/id/123456'
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
