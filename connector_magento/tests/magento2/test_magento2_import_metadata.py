# Copyright 2013-2019 Camptocamp SA
# Copyright 2020 Opener B.V.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from .common import Magento2TestCase, recorder


class TestImportMetadata(Magento2TestCase):

    def test_import_backend(self):
        """ Synchronize initial metadata """
        with recorder.use_cassette('metadata'):
            self.backend.synchronize_metadata()

        website_model = self.env['magento.website']
        websites = website_model.search(
            [('backend_id', '=', self.backend.id)]
        )
        self.assertEqual(len(websites), 1)

        store_model = self.env['magento.store']
        stores = store_model.search([('backend_id', '=', self.backend.id)])
        self.assertEqual(len(stores), 1)

        storeview_model = self.env['magento.storeview']
        storeview = storeview_model.search(
            [('backend_id', '=', self.backend.id)])
        self.assertEqual(len(storeview), 1)
        self.assertEqual(storeview.base_media_url, 'http://magento/media/')
