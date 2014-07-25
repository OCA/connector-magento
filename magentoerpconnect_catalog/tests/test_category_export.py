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
from openerp.addons.magentoerpconnect_catalog.product_category import (
    export_product_category_image)
from .test_data import magento_attribute_responses

IMAGE = ("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAMAAAAoyzS7AA"
         "AAA1BMVEUAAACnej3aAAAAAXRSTlMA\nQObYZgAAAA1JRE"
         "FUeNoBAgD9/wAAAAIAAVMrnDAAAAAASUVORK5CYII=\n")


class TestExportCategory(SetUpMagentoSynchronized):
    """ Test the export from a Magento Mock.

    The data returned by Magento are those created for the
    demo version of Magento on a standard 1.7 version.
    """
    
    def get_magento_id(self):
        cr = self.cr
        cr.execute("SELECT max(magento_id::int) FROM magento_product_category")
        result = cr.fetchone()
        if result:
            return int(result[0]) + 1
        else:
            return 1

    def test_10_export_category(self):
        """ Test export of category"""
        response = {
            'catalog_category.create': self.get_magento_id(),
        }
        cr = self.cr
        uid = self.uid
        with mock_api(response, key_func=lambda m, a: m) as calls_done:
            mag_categ_model = self.registry('magento.product.category')
            mag_categ_id = mag_categ_model.create(cr, uid, {
                'name': 'My Category',
                'backend_id': self.backend_id,
                })
            
            export_record(self.session, 'magento.product.category',
                          mag_categ_id)

            self.assertEqual(len(calls_done), 1)
            method, (parent_id, data) = calls_done[0]
            self.assertEqual(method, 'catalog_category.create')
            self.assertEqual(parent_id, 1)

    def test_20_export_category_with_image(self):
        """ Test export of category"""
        response = {
            'catalog_category.create': self.get_magento_id(),
            'ol_catalog_category_media.create': 'true',
        }
        cr = self.cr
        uid = self.uid
        with mock_api(response, key_func=lambda m, a: m) as calls_done:
            mag_categ_model = self.registry('magento.product.category')
            mag_categ_id = mag_categ_model.create(cr, uid, {
                'name': 'My Category',
                'image': IMAGE,
                'image_name': 'myimage.png',
                'backend_id': self.backend_id,
                })
            
            export_record(self.session, 'magento.product.category',
                          mag_categ_id)
            export_product_category_image(
                self.session,
                'magento.product.category',
                mag_categ_id)

            self.assertEqual(len(calls_done), 2)
            method, (parent_id, data) = calls_done[0]
            self.assertEqual(method, 'catalog_category.create')
            self.assertEqual(parent_id, 1)
            self.assertEqual(data['image'], 'myimage.png')
            self.assertEqual(data['thumbnail'], 'myimage.png')
            self.assertEqual(data['name'], 'My Category')

            method, (image_name, image_data) = calls_done[1]
            self.assertEqual(method, 'ol_catalog_category_media.create')
            self.assertEqual(parent_id, 1)
            self.assertEqual(image_name, 'myimage.png')
            self.assertEqual(image_data, IMAGE)
