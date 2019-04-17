# Copyright 2013-2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from .common import MagentoTestCase, recorder


class TestImportMetadata(MagentoTestCase):

    def test_import_backend(self):
        """ Synchronize initial metadata """
        with recorder.use_cassette('metadata'):
            self.backend.synchronize_metadata()

            website_model = self.env['magento.website']
            websites = website_model.search(
                [('backend_id', '=', self.backend.id)]
            )
            self.assertEqual(len(websites), 2)

            store_model = self.env['magento.store']
            stores = store_model.search([('backend_id', '=', self.backend.id)])
            self.assertEqual(len(stores), 2)

            storeview_model = self.env['magento.storeview']
            storeviews = storeview_model.search(
                [('backend_id', '=', self.backend.id)])
            self.assertEqual(len(storeviews), 4)
