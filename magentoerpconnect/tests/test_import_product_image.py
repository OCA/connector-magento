# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2013 Camptocamp SA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import urllib2
import mock
from base64 import b64encode

from openerp.addons.magentoerpconnect.unit.import_synchronizer import (
    import_batch, import_record)
from openerp.addons.connector.session import ConnectorSession
import openerp.tests.common as common
from .common import mock_api, MockResponseImage
from .data_base import magento_base_responses
from .data_product import simple_product_and_images
from openerp.addons.magentoerpconnect.product import (
    CatalogImageImporter,
    ProductProductAdapter,
)

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
                     "\x00\x00IEND\xaeB`\x82")
B64_PNG_IMG_4PX_GREEN = b64encode(PNG_IMG_4PX_GREEN)


class TestImportProductImage(common.TransactionCase):
    """ Test the imports of the image of the products. """

    def setUp(self):
        super(TestImportProductImage, self).setUp()
        backend_model = self.env['magento.backend']
        warehouse = self.env.ref('stock.warehouse0')
        self.backend_id = backend_model.create(
            {'name': 'Test Magento',
             'version': '1.7',
             'location': 'http://anyurl',
             'username': 'guewen',
             'warehouse_id': warehouse.id,
             'password': '42'}).id

        self.session = ConnectorSession(self.env.cr, self.env.uid,
                                        context=self.env.context)
        with mock_api(magento_base_responses):
            import_batch(self.session, 'magento.website', self.backend_id)
            import_batch(self.session, 'magento.store', self.backend_id)
            import_batch(self.session, 'magento.storeview', self.backend_id)
            import_record(self.session, 'magento.product.category',
                          self.backend_id, 1)

        self.product_model = self.env['magento.product.product']

    def test_image_priority(self):
        """ Check if the images are sorted in the correct priority """
        env = mock.Mock()
        importer = CatalogImageImporter(env)
        file1 = {'file': 'file1', 'types': ['image'], 'position': '10'}
        file2 = {'file': 'file2', 'types': ['thumbnail'], 'position': '3'}
        file3 = {'file': 'file3', 'types': ['thumbnail'], 'position': '4'}
        file4 = {'file': 'file4', 'types': [], 'position': '10'}
        images = [file2, file1, file4, file3]
        self.assertEquals(importer._sort_images(images),
                          [file4, file3, file2, file1])

    def test_import_images_404(self):
        """ An image responds a 404 error, skip and take the first valid """
        env = mock.MagicMock()
        env.get_connector_unit.return_value = ProductProductAdapter(env)
        model = mock.MagicMock(name='model')
        model.browse.return_value = model
        env.model.with_context.return_value = model

        importer = CatalogImageImporter(env)
        url_tee1 = ('http://localhost:9100/media/catalog/product'
                    '/i/n/ink-eater-krylon-bombear-destroyed-tee-1.jpg')
        url_tee2 = ('http://localhost:9100/media/catalog/product/'
                    'i/n/ink-eater-krylon-bombear-destroyed-tee-2.jpg')
        with mock.patch('urllib2.urlopen') as urlopen:
            def image_url_response(url):
                if url._Request__original in (url_tee1, url_tee2):
                    raise urllib2.HTTPError(url, 404, '404', None, None)
                else:
                    return MockResponseImage(PNG_IMG_4PX_GREEN)

            urlopen.side_effect = image_url_response
            with mock_api(simple_product_and_images):
                importer.run(122, 999)

        model.browse.assert_called_with(999)
        model.write.assert_called_with({'image': B64_PNG_IMG_4PX_GREEN})

    def test_import_images_403(self):
        """ Import a product when an image respond a 403 error, should fail """
        env = mock.MagicMock()
        env.get_connector_unit.return_value = ProductProductAdapter(env)
        importer = CatalogImageImporter(env)
        url_tee1 = ('http://localhost:9100/media/catalog/product'
                    '/i/n/ink-eater-krylon-bombear-destroyed-tee-1.jpg')
        url_tee2 = ('http://localhost:9100/media/catalog/product/'
                    'i/n/ink-eater-krylon-bombear-destroyed-tee-2.jpg')
        with mock.patch('urllib2.urlopen') as urlopen:
            def image_url_response(url):
                url = url.get_full_url()
                if url == url_tee2:
                    raise urllib2.HTTPError(url, 404, '404', None, None)
                elif url == url_tee1:
                    raise urllib2.HTTPError(url, 403, '403', None, None)
                else:
                    return MockResponseImage(PNG_IMG_4PX_GREEN)

            urlopen.side_effect = image_url_response
            with mock_api(simple_product_and_images):
                with self.assertRaises(urllib2.HTTPError):
                    importer.run(122, 999)
