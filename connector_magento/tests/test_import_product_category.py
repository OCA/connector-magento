# Copyright 2013-2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from .common import MagentoSyncTestCase, recorder


class TestImportProductCategory(MagentoSyncTestCase):

    @recorder.use_cassette
    def test_import_product_category(self):
        """ Import of a product category """
        backend_id = self.backend.id

        self.env['magento.product.category'].import_record(self.backend, '1')

        category_model = self.env['magento.product.category']
        category = category_model.search([('backend_id', '=', backend_id)])
        self.assertEqual(len(category), 1)

    @recorder.use_cassette
    def test_import_product_category_with_gap(self):
        """ Import of a product category when parent categories are missing """
        backend_id = self.backend.id

        self.env['magento.product.category'].import_record(self.backend, '26')

        category_model = self.env['magento.product.category']
        categories = category_model.search([('backend_id', '=', backend_id)])
        # tree: Women > Sale > Default Category > Test Magento (hidden)
        self.assertEqual(len(categories), 4)
