# Copyright 2015-2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import urllib.error
import mock
from base64 import b64encode

from odoo import models
from odoo.addons.component.core import WorkContext, Component
from odoo.addons.component.tests.common import (
    TransactionComponentRegistryCase,
)
from .. import components
from ..models.product.importer import CatalogImageImporter
from .common import MockResponseImage

# simple square of 4 px filled with green in png, used for the product
# images
PNG_IMG_4PX_GREEN = ("\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x04"
                     "\x00\x00\x00\x04\x08\x02\x00\x00\x00&\x93\t)\x00\x00"
                     "\x00\x01sRGB\x00\xae\xce\x1c\xe9\x00\x00\x00\tpHYs"
                     "\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18"
                     "\x00\x00\x00\x07tIME\x07\xdd\t\x02\t\x1d0\x13\th\x94"
                     "\x00\x00\x00\x19tEXtComment\x00Created with GIMPW\x81"
                     "\x0e\x17\x00\x00\x00\x12IDAT\x08\xd7cd\xf8\xcf\x00\x07L"
                     "\x0c\x0c\xc4p\x002\xd2\x01\x07\xce\xee\xd0\xcf\x00\x00"
                     "\x00\x00IEND\xaeB`\x82".encode('utf-8'))
B64_PNG_IMG_4PX_GREEN = b64encode(PNG_IMG_4PX_GREEN)


class TestImportProductImage(TransactionComponentRegistryCase):
    """ Test the imports of the image of the products. """

    def setUp(self):
        super(TestImportProductImage, self).setUp()
        self.backend_model = self.env['magento.backend']
        warehouse = self.env.ref('stock.warehouse0')
        self.backend = self.backend_model.create(
            {'name': 'Test Magento',
             'version': '1.7',
             'location': 'http://magento',
             'username': 'odoo',
             'warehouse_id': warehouse.id,
             'password': 'odoo42'}
        )

        category_model = self.env['product.category']
        existing_category = category_model.create({'name': 'all'})
        self.create_binding_no_export(
            'magento.product.category',
            existing_category,
            1
        )
        self.product_model = self.env['magento.product.product']

        # Use a stub for the product adapter, which is called
        # during the tests by the image importer
        class StubProductAdapter(Component):
            _name = 'stub.product.adapter'
            _collection = 'magento.backend'
            _usage = 'backend.adapter'
            _apply_on = 'magento.product.product'

            def get_images(self, external_id, storeview_id=None, data=None):
                return [
                    {'exclude': '1',
                     'file': '/i/n/ink-eater-krylon-bombear-destroyed-tee-2.jpg',  # noqa
                     'label': '',
                     'position': '0',
                     'types': ['thumbnail'],
                     'url': 'http://localhost:9100/media/catalog/product/i/n/ink-eater-krylon-bombear-destroyed-tee-2.jpg'},  # noqa
                    {'exclude': '0',
                     'file': '/i/n/ink-eater-krylon-bombear-destroyed-tee-1.jpg',  # noqa
                     'label': '',
                     'position': '3',
                     'types': ['small_image'],
                     'url': 'http://localhost:9100/media/catalog/product/i/n/ink-eater-krylon-bombear-destroyed-tee-1.jpg'},  # noqa
                    {'exclude': '0',
                     'file': '/m/a/connector_magento_1.png',
                     'label': '',
                     'position': '4',
                     'types': [],
                     'url': 'http://localhost:9100/media/catalog/product/m/a/connector_magento_1.png'},  # noqa
                ]

        # build the Stub and the component we want to test
        self._build_components(StubProductAdapter,
                               components.core.BaseMagentoConnectorComponent,
                               components.importer.MagentoImporter,
                               CatalogImageImporter)
        self.work = WorkContext(model_name='magento.product.product',
                                collection=self.backend,
                                components_registry=self.comp_registry)
        self.image_importer = self.work.component_by_name(
            'magento.product.image.importer'
        )

    def create_binding_no_export(self, model_name, odoo_id, external_id=None,
                                 **cols):
        if isinstance(odoo_id, models.BaseModel):
            odoo_id = odoo_id.id
        values = {
            'backend_id': self.backend.id,
            'odoo_id': odoo_id,
            'external_id': external_id,
        }
        if cols:
            values.update(cols)
        return self.env[model_name].with_context(
            connector_no_export=True
        ).create(values)

    def test_image_priority(self):
        """ Check if the images are sorted in the correct priority """
        file1 = {'file': 'file1', 'types': ['image'], 'position': '10'}
        file2 = {'file': 'file2', 'types': ['thumbnail'], 'position': '3'}
        file3 = {'file': 'file3', 'types': ['thumbnail'], 'position': '4'}
        file4 = {'file': 'file4', 'types': [], 'position': '10'}
        images = [file2, file1, file4, file3]
        self.assertEqual(self.image_importer._sort_images(images),
                         [file4, file3, file2, file1])

    def test_import_images_404(self):
        """ An image responds a 404 error, skip and take the first valid """
        url_tee1 = ('http://localhost:9100/media/catalog/product'
                    '/i/n/ink-eater-krylon-bombear-destroyed-tee-1.jpg')
        url_tee2 = ('http://localhost:9100/media/catalog/product/'
                    'i/n/ink-eater-krylon-bombear-destroyed-tee-2.jpg')

        binding = mock.Mock(name='magento.product.product,999')
        binding.id = 999
        binding_no_export = mock.MagicMock(
            name='magento.product.product,999:no_export'
        )
        binding.with_context.return_value = binding_no_export

        with mock.patch('requests.get') as requests_get:
            def image_url_response(url, headers=None, verify=None):
                if url in (url_tee1, url_tee2):
                    return MockResponseImage('', code=404)
                else:
                    return MockResponseImage(PNG_IMG_4PX_GREEN)
            requests_get.side_effect = image_url_response

            self.image_importer.run(111, binding)

        binding.with_context.assert_called_with(connector_no_export=True)
        binding_no_export.write.assert_called_with(
            {'image': B64_PNG_IMG_4PX_GREEN}
        )

    def test_import_images_403(self):
        """ Import a product when an image respond a 403 error, should fail """

        binding = mock.Mock(name='magento.product.product,999')
        binding.id = 999

        url_tee1 = ('http://localhost:9100/media/catalog/product'
                    '/i/n/ink-eater-krylon-bombear-destroyed-tee-1.jpg')
        url_tee2 = ('http://localhost:9100/media/catalog/product/'
                    'i/n/ink-eater-krylon-bombear-destroyed-tee-2.jpg')
        with mock.patch('requests.get') as requests_get:
            def image_url_response(url, headers=None, verify=None):
                if url == url_tee2:
                    raise urllib.error.HTTPError(url, 404, '404', None, None)
                elif url == url_tee1:
                    raise urllib.error.HTTPError(url, 403, '403', None, None)
                return MockResponseImage(PNG_IMG_4PX_GREEN)

            requests_get.side_effect = image_url_response
            with self.assertRaises(urllib.error.HTTPError):
                self.image_importer.run(122, binding)
