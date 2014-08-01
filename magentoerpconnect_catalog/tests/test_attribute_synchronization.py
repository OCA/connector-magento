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
        attr_group_model = self.registry('attribute.group')
        cr, uid = self.cr, self.uid
        self.default_mag_attr_set_id = '9'
        mag_attr_set_ids = mag_attr_set_model.search(cr, uid, [
            ('magento_id', '=', self.default_mag_attr_set_id),
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

        self.attr_group_id = attr_group_model.create(
            cr, uid, {
                'attribute_set_id': attr_set_id,
                'name': 'openerp',
                }, {'force_model': 'product.template'})


class TestExportAttribute(SetUpMagentoSynchronizedWithAttribute):
    """ Test the export from a Magento Mock.

    The data returned by Magento are those created for the
    demo version of Magento on a standard 1.7 version.
    """

    def add_attribute(self, attribute_type, name, code):
        cr = self.cr
        uid = self.uid
        mag_attr_model = self.registry('magento.product.attribute')
        field_model = self.registry('ir.model.fields')
        attr_model = self.registry('attribute.attribute')

        existing_field_ids = field_model.search(cr, uid, [
            ('name', 'ilike', code),
            ])
        # Each time we run the test on the same database
        # OpenERP will commit the attribute, as the code have to be uniq
        # we need to change the code depending of the existing data
        max_offset = 0
        for existing_field in field_model.browse(cr, uid, existing_field_ids):
            offset = int(existing_field.name.replace(code, '').strip('_') or 0)
            if offset > max_offset:
                max_offset = offset
        max_offset += 1
        code = "%s_%s" % (code, max_offset)

        attr_id = attr_model.create(cr, uid, {
            'field_description': name,
            'name': code,
            'attribute_type': attribute_type,
            }, {'force_model': 'product.template'})

        mag_attr_id = mag_attr_model.create(cr, uid, {
            'frontend_label': name,
            'attribute_code': code,
            'openerp_id': attr_id,
            'backend_id': self.backend_id,
            })

        return attr_id, mag_attr_id, code

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
            self.assertEqual(method, 'product_attribute_set.create')
            self.assertEqual(skeleton_id, '9')


    def test_30_export_attribute_char(self):
        response = {
            'product_attribute.create':
                self.get_magento_helper('magento.product.attribute').get_next_id,
        }
        with mock_api(response, key_func=lambda m, a: m) as calls_done:
            attr_id, bind_attr_id, code = self.add_attribute(
                'char', 'My Test Char', 'x_test_char')
   
            export_record(self.session, 'magento.product.attribute',
                          bind_attr_id)

            self.assertEqual(len(calls_done), 1)
            method, (data,) = calls_done[0]
            self.assertEqual(method, 'product_attribute.create')
            self.assertEqual(data['attribute_code'], code)
            self.assertEqual(data['frontend_input'], 'text')

    def test_40_export_attribute_char_linked_to_an_attribute_set(self):
        response = {
            'product_attribute.create':
                self.get_magento_helper('magento.product.attribute').get_next_id,
            'product_attribute_set.attributeAdd': True,
        }
        attr_binder = self.get_binder('magento.product.attribute')
        with mock_api(response, key_func=lambda m, a: m) as calls_done:
            attr_id, bind_attr_id, code = self.add_attribute(
                'char', 'My Test Char', 'x_test_char')
            self.registry('attribute.location').create(self.cr, self.uid, {
                'attribute_id': attr_id,
                'attribute_group_id': self.attr_group_id,
                })

            export_record(self.session, 'magento.product.attribute',
                          bind_attr_id)
            self.assertEqual(len(calls_done), 2)
            method, (data,) = calls_done[0]
            self.assertEqual(method, 'product_attribute.create')

            method, (mag_attr_id, mag_attr_set_id) = calls_done[1]
            self.assertEqual(method, 'product_attribute_set.attributeAdd')
            self.assertEqual(mag_attr_set_id, self.default_mag_attr_set_id)
            expected_mag_attr_id = attr_binder.to_backend(bind_attr_id)
            self.assertEqual(mag_attr_id, expected_mag_attr_id)


    def test_50_autobind_attribute_option(self):
        option_model = self.registry('attribute.option')
        binding_option_model = self.registry('magento.attribute.option')
        response = {
            'product_attribute.create':
                self.get_magento_helper('magento.product.attribute').get_next_id,
        }
        with mock_api(response, key_func=lambda m, a: m) as calls_done:
            attr_id, bind_attr_id, code = self.add_attribute(
                'select', 'My Test Select', 'x_test_select')
            option_id = option_model.create(self.cr, self.uid, {
                'attribute_id': attr_id,
                'name': 'My Option',
                })
            option = option_model.browse(self.cr, self.uid, option_id)
            self.assertEqual(len(option.magento_bind_ids), 1)

    def test_60_export_attribute_option(self):
        option_model = self.registry('attribute.option')
        binding_option_model = self.registry('magento.attribute.option')
        response = {
            'product_attribute.create':
                self.get_magento_helper('magento.product.attribute').get_next_id,
            'oerp_product_attribute.addOption':
                self.get_magento_helper('magento.attribute.option').get_next_id
        }
        attr_binder = self.get_binder('magento.product.attribute')
        with mock_api(response, key_func=lambda m, a: m) as calls_done:
            attr_id, bind_attr_id, code = self.add_attribute(
                'select', 'My Test Select', 'x_test_select')
            option_id = option_model.create(self.cr, self.uid, {
                'attribute_id': attr_id,
                'name': 'My Option',
                })

            option = option_model.browse(self.cr, self.uid, option_id)

            export_record(self.session, 'magento.product.attribute',
                          bind_attr_id)
 
            export_record(self.session, 'magento.attribute.option',
                          option.magento_bind_ids[0].id)

            self.assertEqual(len(calls_done), 2)
            method, (data,) = calls_done[0]
            self.assertEqual(method, 'product_attribute.create')

            method, (mag_attr_id, data) = calls_done[1]
            self.assertEqual(method, 'oerp_product_attribute.addOption')
            expected_mag_attr_id = attr_binder.to_backend(bind_attr_id)
            self.assertEqual(mag_attr_id, expected_mag_attr_id)
            self.assertEqual(data['label'][0]['value'], 'My Option')

    def test_70_export_attribute_option_with_dependency(self):
        option_model = self.registry('attribute.option')
        binding_option_model = self.registry('magento.attribute.option')
        response = {
            'product_attribute.create':
                self.get_magento_helper('magento.product.attribute').get_next_id,
            'oerp_product_attribute.addOption':
                self.get_magento_helper('magento.attribute.option').get_next_id
        }
        with mock_api(response, key_func=lambda m, a: m) as calls_done:
            attr_id, bind_attr_id, code = self.add_attribute(
                'select', 'My Test Select', 'x_test_select')
            option_id = option_model.create(self.cr, self.uid, {
                'attribute_id': attr_id,
                'name': 'My Option',
                })

            option = option_model.browse(self.cr, self.uid, option_id)
            export_record(self.session, 'magento.attribute.option',
                          option.magento_bind_ids[0].id)
            
            self.assertEqual(len(calls_done), 2)
            method, (data,) = calls_done[0]
            self.assertEqual(method, 'product_attribute.create')
            method, (mag_attr_id, data) = calls_done[1]
            self.assertEqual(method, 'oerp_product_attribute.addOption')



    #TODO add test with translation
