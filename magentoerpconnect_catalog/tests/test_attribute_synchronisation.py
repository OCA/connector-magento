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
from .test_data import magento_attribute_responses


class TestImportAttribute(SetUpMagentoSynchronized):
    """ Test the import from a Magento Mock.

    The data returned by Magento are those created for the
    demo version of Magento on a standard 1.7 version.
    """

    def test_10_import_attribute_set(self):
        """ Import the default attribute set"""
        with mock_api(magento_attribute_responses):
            import_record(self.session, 'magento.attribute.set',
                          self.backend_id, '9')

        mag_attr_obj = self.registry('magento.attribute.set')
        cr, uid = self.cr, self.uid
        mag_attr_set_ids = mag_attr_obj.search(cr, uid, [
            ('magento_id', '=', '9'),
            ('backend_id', '=', self.backend_id),
            ])
        self.assertEqual(len(mag_attr_set_ids), 1)
        mag_attr_set = mag_attr_obj.browse(cr, uid, mag_attr_set_ids[0])
        self.assertEqual(mag_attr_set.attribute_set_name, 'Default')


class SetUpMagentoSynchronizedWithAttribute(SetUpMagentoSynchronized):
    
    def setUp(self):
        super(SetUpMagentoSynchronizedWithAttribute, self).setUp()
        with mock_api(magento_attribute_responses):
            import_record(self.session, 'magento.attribute.set',
                          self.backend_id, '9')

        mag_attr_set_model = self.registry('magento.attribute.set')
        attr_set_model = self.registry('attribute.set')
        cr, uid = self.cr, self.uid
        mag_attr_set_ids = mag_attr_set_model.search(cr, uid, [
            ('magento_id', '=', '9'),
            ('backend_id', '=', self.backend_id),
            ])
        mag_attr_set_id = mag_attr_set_ids[0]
        self.registry('magento.backend').write(cr, uid, self.backend_id, {
            'attribute_set_tpl_id': mag_attr_set_id
            })
        attr_set_id = attr_set_model.create(cr, uid, {
            'name': 'Default Attribute Set',
            }, {'force_model': 'product.template'})

        mag_attr_set_model.write(cr, uid, mag_attr_set_id, {
            'openerp_id': attr_set_id,
            })
        self.default_attr_set_id = attr_set_id



class TestExportAttribute(SetUpMagentoSynchronizedWithAttribute):
    """ Test the export from a Magento Mock.

    The data returned by Magento are those created for the
    demo version of Magento on a standard 1.7 version.
    """

    def test_20_export_attribute_set(self):
        """ Test export of attribute set"""
        response = {
            'product_attribute_set.create': 69,
        }
        cr = self.cr
        uid = self.uid
        with mock_api(response, key_func=lambda m, a: m) as calls_done:
            mag_attr_set_model = self.registry('magento.attribute.set')
            attr_set_model = self.registry('attribute.set')

            attr_set_id = attr_set_model.create(cr, uid, {
                'name': 'Test Export Attribute',
                }, {'force_model': 'product.template'})
            mag_attr_set_id = mag_attr_set_model.create(cr, uid, {
                'attribute_set_name': 'Test Export Attribute',
                'openerp_id': attr_set_id,
                'backend_id': self.backend_id,
                })
            
            export_record(self.session, 'magento.attribute.set',
                          mag_attr_set_id)

            self.assertEqual(len(calls_done), 1)

            method, (data, skeleton_id) = calls_done[0]
            print data
            self.assertEqual(method, 'product_attribute_set.create')
            self.assertEqual(skeleton_id, '9')
