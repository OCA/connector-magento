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

from openerp.addons.magentoerpconnect.tests.test_synchronization import SetpUpMagentoSynchronized
from openerp.addons.magentoerpconnect.unit.import_synchronizer import import_record
from openerp.addons.magentoerpconnect.tests.common import (mock_api,
                                                           mock_urlopen_image)
from .test_data import magento_bundle_responses
from openerp.addons.connector.connector import Binder
from openerp.addons.magentoerpconnect.connector import get_environment


class TestImportMagento(SetpUpMagentoSynchronized):
    """ Test the imports from a Magento Mock.
    """

    def test_15_import_product_bundle(self):
        """ Bundle should fail: not yet supported """
        backend_id = self.backend_id
        with mock_api(magento_bundle_responses):
            import_record(self.session,
                          'magento.product.product',
                          backend_id, 164)
        mag_product_model =  self.registry('magento.product.product')
        mag_product_ids = mag_product_model.search(self.cr,
                                       self.uid,
                                       [('backend_id', '=', backend_id),
                                        ('magento_id', '=', '164')])
        self.assertEqual(len(mag_product_ids), 1)
        mag_product = mag_product_model.browse(self.cr,
                                               self.uid,
                                               mag_product_ids[0])
        self.assertEqual(mag_product.product_type, 'bundle')
        self.assertEqual(mag_product.type, 'service')

    def test_35_import_sale_order_with_bundle(self):
        """ Import a sale order with bundle product """
        backend_id = self.backend_id
        with mock_api(magento_bundle_responses):
            with mock_urlopen_image():
                import_record(self.session,
                              'magento.sale.order',
                              backend_id, '300000031')
        mag_order_model = self.registry('magento.sale.order')
        mag_order_ids = mag_order_model.search(self.cr,
                                       self.uid,
                                       [('backend_id', '=', backend_id),
                                        ('magento_id', '=', '300000031')])
        self.assertEqual(len(mag_order_ids), 1)
        mag_order = mag_order_model.browse(self.cr,
                                           self.uid,
                                           mag_order_ids[0])
        match_line = [
            {'mag_id': None, 'price': 32.33, 'nb_children': 0, 'parent_item_id': False},
            {'mag_id': '165', 'price': 0.00, 'nb_children': 5, 'parent_item_id': False},
            {'mag_id': '138', 'price': 103.93, 'nb_children': 0, 'parent_item_id': '212'},
            {'mag_id': '148', 'price': 68.58, 'nb_children': 0, 'parent_item_id': '212'},
            {'mag_id': '150', 'price': 207.16, 'nb_children': 0, 'parent_item_id': '212'},
            {'mag_id': '141', 'price': 104.61, 'nb_children': 0, 'parent_item_id': '212'},
            {'mag_id': '152', 'price': 484.98, 'nb_children': 0, 'parent_item_id': '212'},
            {'mag_id': '164', 'price': 5311.73, 'nb_children': 5, 'parent_item_id': False},
            {'mag_id': '139', 'price': 0.00, 'nb_children': 0, 'parent_item_id': '218'},
            {'mag_id': '153', 'price': 0.00, 'nb_children': 0, 'parent_item_id': '218'},
            {'mag_id': '143', 'price': 0.00, 'nb_children': 0, 'parent_item_id': '218'},
            {'mag_id': '154', 'price': 0.00, 'nb_children': 0, 'parent_item_id': '218'},
            {'mag_id': '160', 'price': 0.00, 'nb_children': 0, 'parent_item_id': '218'},
            {'mag_id': '166', 'price': 750.00, 'nb_children': 0, 'parent_item_id': False},
        ]

        product_env = get_environment(self.session, 'magento.product.product', backend_id)
        product_binder = product_env.get_connector_unit(Binder)
        line_env = get_environment(self.session, 'magento.sale.order.line', backend_id)
        line_binder = line_env.get_connector_unit(Binder)
        for index, line in enumerate(mag_order.order_line):
            ref_line = match_line[index]
            mag_product_id = product_binder.to_backend(line.product_id.id, wrap=True)
            self.assertEqual(mag_product_id, ref_line['mag_id'])
            product_price = line.price_unit
            self.assertEqual(product_price, ref_line['price'])
            self.assertEqual(len(line.line_child_ids), ref_line['nb_children'])
            if line.line_parent_id:
                mag_parent_line_id = line_binder.to_backend(line.line_parent_id.id, wrap=True)
            else:
                mag_parent_line_id = False
            self.assertEqual(mag_parent_line_id, ref_line['parent_item_id'])
