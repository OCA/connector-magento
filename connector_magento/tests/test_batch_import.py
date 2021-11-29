# Copyright 2020 Opener B.V.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)
from datetime import timedelta
from odoo.fields import Datetime
from .common import MagentoSyncTestCase


class TestBatchImport(MagentoSyncTestCase):
    def test_order_import_delay(self):
        """ Batch import delay is honoured when importing orders """
        storeview = self.env['magento.storeview'].search(
            [('backend_id', '=', self.backend.id)], limit=1)
        max_job_id = self.env['queue.job'].search(
            [], order='id desc', limit=1).id or 0
        self.backend.order_import_delay = 35
        now = Datetime.now()
        original_from_date = now - timedelta(hours=2)
        storeview.import_orders_from_date = original_from_date
        storeview.import_sale_orders()
        job = self.env['queue.job'].search([('id', '>', max_job_id)])
        self.assertTrue(job)
        self.assertAlmostEqual(
            Datetime.to_datetime(job.kwargs['filters']['from_date']),
            original_from_date)
        expected_to_date = now - timedelta(minutes=35)
        to_date = Datetime.to_datetime(job.kwargs['filters']['to_date'])
        self.assertAlmostEqual(to_date, expected_to_date, delta=timedelta(1))
        self.assertAlmostEqual(
            to_date, storeview.import_orders_from_date, delta=timedelta(1))
