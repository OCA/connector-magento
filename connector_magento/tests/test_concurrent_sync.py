# Copyright 2015-2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import mock

from odoo import api
from odoo.tests import common
from odoo.modules.registry import Registry

from odoo.addons.queue_job.exception import RetryableJobError
from odoo.addons.component.core import WorkContext

from .common import MagentoTestCase


class TestConcurrentSync(MagentoTestCase):

    def setUp(self):
        super(TestConcurrentSync, self).setUp()
        self.registry2 = Registry.registries.get(common.get_db_name())
        self.cr2 = self.registry2.cursor()
        self.env2 = api.Environment(self.cr2, self.env.uid, {})

        @self.addCleanup
        def reset_cr2():
            # rollback and close the cursor, and reset the environments
            self.env2.reset()
            self.cr2.rollback()
            self.cr2.close()

        backend2 = mock.MagicMock(name='Backend Record')
        backend2._name = 'magento.backend'
        backend2.id = self.backend.id
        backend2.env = self.env2
        self.backend2 = backend2

    def test_concurrent_import(self):
        api_client = mock.MagicMock(name='Magento API')
        api_client.call.return_value = {
            'name': 'Root',
            'description': '',
            'level': '1',
        }
        work = WorkContext(model_name='magento.product.category',
                           collection=self.backend,
                           magento_api=api_client)
        importer = work.component_by_name('magento.product.category.importer')
        importer.run(1)

        work2 = WorkContext(model_name='magento.product.category',
                            collection=self.backend2,
                            magento_api=api_client)
        importer2 = work2.component_by_name(
            'magento.product.category.importer'
        )
        with self.assertRaises(RetryableJobError):
            importer2.run(1)
