# Copyright 2013-2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from openerp.addons.connector.exception import InvalidDataError
from .common import MagentoSyncTestCase, recorder, mock_urlopen_image


class TestImportProduct(MagentoSyncTestCase):

    def setUp(self):
        super(TestImportProduct, self).setUp()

    def _create_category(self, name, external_id):
        category_model = self.env['product.category']
        category = category_model.create({'name': name})
        self.create_binding_no_export(
            'magento.product.category', category, external_id
        )

    @recorder.use_cassette
    def test_import_product(self):
        """ Import of a simple product """
        backend_id = self.backend.id

        # create the magento category of this product
        self._create_category('Eyewear', 18)

        with mock_urlopen_image():
            # the category of this product has category magento id 18,
            # so we already have it
            self.env['magento.product.product'].import_record(
                self.backend, '337'
            )

        product_model = self.env['magento.product.product']
        product = product_model.search([('backend_id', '=', backend_id),
                                        ('external_id', '=', '337')])
        self.assertEqual(len(product), 1)

    @recorder.use_cassette
    def test_import_product_category_missing(self):
        """ Import of a simple product when the category is missing """
        backend_id = self.backend.id
        self.assertEqual(len(self.env['magento.product.category'].search(
            [('backend_id', '=', backend_id)]
        )), 0)

        with mock_urlopen_image():
            self.env['magento.product.product'].import_record(
                self.backend, '382'
            )

        product_model = self.env['magento.product.product']
        product = product_model.search([('backend_id', '=', backend_id),
                                        ('external_id', '=', '382')])
        self.assertEqual(len(product), 1)
        # category should have been imported in cascade
        self.assertEqual(len(self.env['magento.product.category'].search(
            [('backend_id', '=', backend_id)]
        )), 4)

    @recorder.use_cassette
    def test_import_product_configurable(self):
        """ Import of a configurable product : no need to import it

        The 'configurable' part of the product does not need to be imported,
        we import only the variants
        """
        backend_id = self.backend.id

        self.env['magento.product.product'].import_record(
            self.backend, '408'
        )

        product_model = self.env['magento.product.product']
        products = product_model.search([('backend_id', '=', backend_id),
                                         ('external_id', '=', '408')])
        self.assertEqual(len(products), 0)

    @recorder.use_cassette
    def test_import_product_bundle(self):
        """ Bundle should fail: not yet supported """
        with self.assertRaises(InvalidDataError):
            self.env['magento.product.product'].import_record(
                self.backend, '447'
            )

    @recorder.use_cassette
    def test_import_product_grouped(self):
        """ Grouped should fail: not yet supported """
        with self.assertRaises(InvalidDataError):
            self.env['magento.product.product'].import_record(
                self.backend, '555'
            )

    @recorder.use_cassette
    def test_import_product_virtual(self):
        """ Virtual products are created as service products """
        backend_id = self.backend.id

        self.env['magento.product.product'].import_record(
            self.backend, '563'
        )

        product_model = self.env['magento.product.product']
        product = product_model.search([('backend_id', '=', backend_id),
                                        ('external_id', '=', '563')])
        self.assertEqual(product.type, 'service')
