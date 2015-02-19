# -*- coding: utf-8 -*-
import mock

import openerp
import openerp.tests.common as common
from openerp.addons.connector.queue.job import (
    Job,
    OpenERPJobStorage,
)
from openerp.addons.connector.session import (
    ConnectorSession)
from .common import mock_api
from .test_data import magento_base_responses
from ..unit.import_synchronizer import import_batch, import_record
from ..unit.export_synchronizer import export_record


class test_related_action_storage(common.TransactionCase):
    """ Test related actions on stored jobs """

    def setUp(self):
        super(test_related_action_storage, self).setUp()
        cr, uid = self.cr, self.uid
        backend_model = self.registry('magento.backend')
        self.session = ConnectorSession(cr, uid)
        self.session.context['__test_no_commit'] = True
        warehouse_id = self.ref('stock.warehouse0')
        backend_id = backend_model.create(
            cr,
            uid,
            {'name': 'Test Magento',
                'version': '1.7',
                'location': 'http://anyurl',
                'username': 'username',
                'warehouse_id': warehouse_id,
                'password': '42'})
        self.backend = backend_model.browse(cr, uid, backend_id)
        # import the base informations
        with mock_api(magento_base_responses):
            import_batch(self.session, 'magento.website', backend_id)
            import_batch(self.session, 'magento.store', backend_id)
            import_batch(self.session, 'magento.storeview', backend_id)
        self.MagentoProduct = self.registry('magento.product.product')
        self.QueueJob = self.registry('queue.job')

    def test_unwrap_binding(self):
        """ Open a related action opening an unwrapped binding """
        cr, uid = self.cr, self.uid
        product_id = self.ref('product.product_product_7')
        magento_product_id = self.MagentoProduct.create(
            cr, uid,
            {'openerp_id': product_id,
             'backend_id': self.backend.id})
        stored = self._create_job(export_record, 'magento.product.product',
                                  magento_product_id)
        expected = {
            'name': mock.ANY,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': product_id,
            'res_model': 'product.product',
        }
        self.assertEquals(stored.open_related_action(), expected)

    def _create_job(self, func, *args):
        cr, uid = self.cr, self.uid
        job = Job(func=func, args=args)
        storage = OpenERPJobStorage(self.session)
        storage.store(job)
        stored_ids = self.QueueJob.search(self.cr, self.uid,
                                          [('uuid', '=', job.uuid)])
        self.assertEqual(len(stored_ids), 1)
        return self.QueueJob.browse(cr, uid, stored_ids[0])

    def test_link(self):
        """ Open a related action opening an url on Magento """
        self.backend.write({'admin_location': 'http://www.example.com/admin'})
        self.backend.refresh()
        stored = self._create_job(import_record, 'magento.product.product',
                                  self.backend.id, 123456)
        url = 'http://www.example.com/admin/catalog_product/edit/id/123456'
        expected = {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': url,
        }
        self.assertEquals(stored.open_related_action(), expected)

    def test_link_no_location(self):
        """ Related action opening an url, admin location is not configured """
        self.backend.write({'admin_location': False})
        self.backend.refresh()
        stored = self._create_job(import_record, 'magento.product.product',
                                  self.backend.id, 123456)
        with self.assertRaises(openerp.osv.orm.except_orm):
            stored.open_related_action()
