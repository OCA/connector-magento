# Copyright 2015-2019 Camptocamp SA
# Copyright 2020 Opener B.V.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)
from ..test_import_product_image import TestImportProductImage


class TestImportProductImageMagento2(TestImportProductImage):
    """ Test the imports of the image of the products. """

    @classmethod
    def setUpClass(cls):
        super(TestImportProductImageMagento2, cls).setUpClass()
        warehouse = cls.env.ref('stock.warehouse0')
        cls.backend = cls.backend_model.create(
            {'name': 'Test Magento',
             'version': '2.0',
             'location': 'http://magento',
             'warehouse_id': warehouse.id,
             'token': 'odoo42'}
        )
