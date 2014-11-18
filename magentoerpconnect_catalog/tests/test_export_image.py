# -*- coding: utf-8 -*-
###############################################################################
#
#   Module for OpenERP
#   Copyright (C) 2014 Akretion (http://www.akretion.com).
#   @author Sébastien BEAU <sebastien.beau@akretion.com>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as
#   published by the Free Software Foundation, either version 3 of the
#   License, or (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

from openerp.addons.magentoerpconnect.tests.test_synchronization import (
    SetUpMagentoSynchronized)
from openerp.addons.magentoerpconnect.unit.import_synchronizer import (
    import_record)
from openerp.addons.magentoerpconnect.tests.common import (
    mock_api,
    mock_urlopen_image)
from openerp.addons.magentoerpconnect.unit.export_synchronizer import (
    export_record)

IMAGE = ("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAMAAAAoyzS7AA"
         "AAA1BMVEUAAACnej3aAAAAAXRSTlMA\nQObYZgAAAA1JRE"
         "FUeNoBAgD9/wAAAAIAAVMrnDAAAAAASUVORK5CYII=\n")

class SetUpImage(SetUpMagentoSynchronized):
    """ Test the import from a Magento Mock.

    The data returned by Magento are those created for the
    demo version of Magento on a standard 1.7 version.
    """

    def setUp(self):
        super(SetUpMagentoSynchronized, self).setUp()
        self.mag_product_model = self.registry('magento.product.product')
        self.magento_product_id = self.get_magento_helper(
            'magento.product.product').get_next_id()
        self.product_binding_id = self.mag_product_model.create(
            self.cr, self.uid, {
                'name': 'My product with image',
                'magento_id': self.magento_product_id,
                'backend_id': self.backend_id,
                })
        mag_product = self.mag_product_model.browse(
            self.cr, self.uid, self.product_binding_id)
        self.product_id = mag_product.openerp_id.id

    def add_image(self, name, sequence=1):
        image_model = self.registry('product.image')
        return image_model.create(self.cr, self.uid, {
            'name': name,
            'file_name': '%s.jpg' % name,
            'sequence': sequence,
            'product_id': self.product_id,
            'image': IMAGE, 
            })

    def get_image_binding(self, image_id):
        mag_image_model = self.registry('magento.product.image')
        return mag_image_model.search(self.cr, self.uid, [
            ('openerp_id', '=', image_id),
            ('backend_id', '=', self.backend_id),
            ])
    
    def active_autobind(self):
        self.backend_model.write(self.cr, self.uid, self.backend_id, {
            'auto_bind_image': True,
            })

    def unactive_autobind(self):
        self.backend_model.write(self.cr, self.uid, self.backend_id, {
            'auto_bind_image': False,
            })


class TestAutoBindImage(SetUpImage):

    def test_10_no_autobind(self):
        self.unactive_autobind()
        image_id = self.add_image('image_test')
        binding_ids = self.get_image_binding(image_id)
        self.assertEqual(len(binding_ids), 0)

    def test_20_autobind(self):
        self.active_autobind()
        image_id = self.add_image('image_test')
        binding_ids = self.get_image_binding(image_id)
        self.assertEqual(len(binding_ids), 1)


class TestExportImage(SetUpImage):
    """ Test the export from a Magento Mock.

    The data returned by Magento are those created for the
    demo version of Magento on a standard 1.7 version.
    """
    
    def setUp(self):
        super(TestExportImage, self).setUp()
        self.active_autobind()
        self.image_1_id = self.add_image('image_1', 1)
        self.mag_image_1_id = self.get_image_binding(self.image_1_id)[0]
        self.image_2_id = self.add_image('image_2', 2)
        self.mag_image_2_id = self.get_image_binding(self.image_2_id)[0]
        self.image_helper = self.get_magento_helper('magento.product.image')

    def check_image_call(self, call_done, result_expected):
        method, (product_id, data, storeview_id) = call_done
        self.assertEqual(method, 'catalog_product_attribute_media.create')
        self.assertEqual(int(product_id), self.magento_product_id)
        df = data['file']
        rf = result_expected['file']
        self.assertEqual(df['content'], rf['content'])
        self.assertEqual(df['mime'], rf['mime'])
        self.assertEqual(df['name'], rf['name'])
        self.assertEqual(data['position'], result_expected['position'])
        self.assertEqual(data['label'], result_expected['label'])
        self.assertEqual(data['types'], result_expected['types'])

    def test_10_export_one_image(self):
        """ Export one Image """
        response = {
            'catalog_product_attribute_media.create':
                self.image_helper.get_next_id,
        }
 
        with mock_api(response, key_func=lambda m, a: m) as calls_done:
            export_record(self.session, 'magento.product.image',
                          self.mag_image_1_id)

            self.assertEqual(len(calls_done), 1)
            result_expected = {
                'file': {
                    'content': IMAGE,
                    'name': 'image_1',
                    'mime': 'image/jpeg',
                },
                'label': 'image_1',
                'types': ['image', 'small_image', 'thumbnail'],
                'position': 1,
                }
            self.check_image_call(calls_done[0], result_expected)

    def test_20_export_two_image(self):
        """ Export two Images """
        response = {
            'catalog_product_attribute_media.create':
                self.image_helper.get_next_id,
        }
 
        with mock_api(response, key_func=lambda m, a: m) as calls_done:
            export_record(self.session, 'magento.product.image',
                          self.mag_image_1_id)
            export_record(self.session, 'magento.product.image',
                          self.mag_image_2_id)

            self.assertEqual(len(calls_done), 2)
            result_expected_1 = {
                'file': {
                    'content': IMAGE,
                    'name': 'image_1',
                    'mime': 'image/jpeg',
                },
                'label': 'image_1',
                'types': ['image', 'small_image', 'thumbnail'],
                'position': 1,
                }
            self.check_image_call(calls_done[0], result_expected_1)

            result_expected_2 = {
                'file': {
                    'content': IMAGE,
                    'name': 'image_2',
                    'mime': 'image/jpeg',
                },
                'label': 'image_2',
                'types': [],
                'position': 2,
                }
            self.check_image_call(calls_done[1], result_expected_2)


