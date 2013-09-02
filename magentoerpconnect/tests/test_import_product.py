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
from base64 import b64decode

from openerp.addons.magentoerpconnect.unit.import_synchronizer import (
    import_batch, import_record)
from openerp.addons.connector.session import ConnectorSession
import openerp.tests.common as common
from .common import mock_api, MockResponseImage
from .test_data import magento_base_responses
from .test_data_product import simple_product_and_images

# simple square of 4 px filled with green in png, used for the product
# images
PNG_IMG_4PX_GREEN = "\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x04\x00\x00\x00\x04\x08\x02\x00\x00\x00&\x93\t)\x00\x00\x00\x01sRGB\x00\xae\xce\x1c\xe9\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x07tIME\x07\xdd\t\x02\t\x1d0\x13\th\x94\x00\x00\x00\x19tEXtComment\x00Created with GIMPW\x81\x0e\x17\x00\x00\x00\x12IDAT\x08\xd7cd\xf8\xcf\x00\x07L\x0c\x0c\xc4p\x002\xd2\x01\x07\xce\xee\xd0\xcf\x00\x00\x00\x00IEND\xaeB`\x82"


class test_import_product(common.TransactionCase):
    """ Test the imports of the products. """

    def setUp(self):
        super(test_import_product, self).setUp()
        backend_model = self.registry('magento.backend')
        warehouse_id = self.ref('stock.warehouse0')
        self.backend_id = backend_model.create(
            self.cr,
            self.uid,
            {'name': 'Test Magento',
             'version': '1.7',
             'location': 'http://anyurl',
             'username': 'guewen',
             'warehouse_id': warehouse_id,
             'password': '42'})

        self.session = ConnectorSession(self.cr, self.uid)
        with mock_api(magento_base_responses):
            import_batch(self.session, 'magento.website', self.backend_id)
            import_batch(self.session, 'magento.store', self.backend_id)
            import_batch(self.session, 'magento.storeview', self.backend_id)
            import_record(self.session, 'magento.product.category',
                          self.backend_id, 1)
        self.session = ConnectorSession(self.cr, self.uid)
        self.product_model = self.registry('magento.product.product')

    def test_import_images_404(self):
        """ Import a product when an image respond a 404 error, should skip and take the first valid """
        with mock.patch('urllib2.urlopen') as urlopen:
            def image_url_response(url):
                if url == 'http://localhost:9100/media/catalog/product/i/n/ink-eater-krylon-bombear-destroyed-tee-2.jpg':
                    print 'gosh'
                    raise urllib2.HTTPError(url, 404, '404', None, None)
                elif url == 'http://localhost:9100/media/catalog/product/i/n/ink-eater-krylon-bombear-destroyed-tee-1.jpg':
                    print 'gosh2'
                    raise urllib2.HTTPError(url, 404, '404', None, None)
                else:
                    print 'haa'
                    return MockResponseImage(PNG_IMG_4PX_GREEN)

            urlopen.side_effect = image_url_response
            with mock_api(simple_product_and_images):
                import_record(self.session, 'magento.product.product',
                              self.backend_id, 122)
        product_ids = self.product_model.search(
            self.cr,
            self.uid,
            [('backend_id', '=', self.backend_id),
             ('magento_id', '=', '122')])
        self.assertEqual(len(product_ids), 1)
        product = self.session.browse('magento.product.product', product_ids[0])
        self.assertTrue(product.image)
        self.assertEquals(b64decode(product.image),
                          PNG_IMG_4PX_GREEN,
                          "The image which does not respond a 404 "
                          "error must be used.")

    def test_import_images_403(self):
        """ Import a product when an image respond a 403 error, should fail """
        with mock.patch('urllib2.urlopen') as urlopen:
            def image_url_response(url):
                if url == 'http://localhost:9100/media/catalog/product/i/n/ink-eater-krylon-bombear-destroyed-tee-2.jpg':
                    raise urllib2.HTTPError(url, 404, '404', None, None)
                elif url == 'http://localhost:9100/media/catalog/product/i/n/ink-eater-krylon-bombear-destroyed-tee-1.jpg':
                    raise urllib2.HTTPError(url, 403, '403', None, None)
                else:
                    return MockResponseImage(PNG_IMG_4PX_GREEN)

            urlopen.side_effect = image_url_response
            with mock_api(simple_product_and_images):
                with self.assertRaises(urllib2.HTTPError):
                    import_record(self.session, 'magento.product.product',
                                  self.backend_id, 122)
