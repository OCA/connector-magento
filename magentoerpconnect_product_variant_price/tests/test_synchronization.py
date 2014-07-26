# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Chafique DELLI
#    Copyright 2014 AKRETION SA
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

from openerp.addons.magentoerpconnect.unit.export_synchronizer import (
    export_record)
from openerp.addons.magentoerpconnect_catalog.tests.test_attribute_synchronization import (
    SetUpMagentoSynchronizedWithAttribute)
from openerp.addons.magentoerpconnect.tests.common import mock_api


class TestExportMagento(SetUpMagentoSynchronizedWithAttribute):
    """
        Test export of dimension value price for Configurable Products to a Magento Mock.
    """

    def setUp(self):
        super(TestExportMagento, self).setUp()

    def test_export_super_attribute_price(self):
        """ Export Super Attribute Price: check """

        response = {
            'ol_catalog_product_link.updateSuperAttributeValues': True
        }
        cr = self.cr
        uid = self.uid
        with mock_api(response, key_func=lambda m, a: m) as calls_done:
            dimension_value_model = self.registry('dimension.value')
            mag_super_attribute_model = self.registry('magento.super.attribute')
            mag_attribute_option_model = self.registry('magento.attribute.option')
            dim_value_id = dimension_value_model.create(
                cr, uid,
                {
                    'dimension_id': 2,
                    'option_id': 7,
                    'price_extra': 0.0,
                    'product_tmpl_id': 56,
                    })

            dimension_value_model.write(
                cr, uid,
                dim_value_id, {
                    'price_extra': 8.0,
                    })
            dim_value = dimension_value_model.browse(cr, uid, dim_value_id)

            super_attribute_id = mag_super_attribute_model.search(cr, uid, [
                ('attribute_id', '=', dim_value.dimension_id.id),
                ('mag_product_display_id.product_tmpl_id', '=', dim_value.product_tmpl_id.id),
                ])[0]
            super_attribute = mag_super_attribute_model.browse(
                cr, uid, super_attribute_id)

            attribute_option_id = mag_attribute_option_model.search(cr, uid, [
                ('openerp_id', '=', dim_value.option_id.id),
            ])[0]
            attribute_option = mag_attribute_option_model.browse(
                cr, uid, attribute_option_id)

            export_record(
                self.session, 'magento.super.attribute', super_attribute_id)

            self.assertEqual(len(calls_done), 1)

            method, data = calls_done[0]
            magento_super_attribute_id = data[0]
            value_index = data[1][4]['value_index']
            pricing_value = data[1][4]['pricing_value']

            self.assertEqual(method, 'ol_catalog_product_link.updateSuperAttributeValues')
            self.assertEqual(magento_super_attribute_id, int(super_attribute.magento_id))
            self.assertEqual(value_index, attribute_option.magento_id)
            self.assertEqual(pricing_value, dim_value.price_extra)
