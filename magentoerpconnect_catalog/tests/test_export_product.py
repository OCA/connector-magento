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

class SetUpProduct(SetUpMagentoSynchronized):
    """ Test the export from a Magento Mock.

    The data returned by Magento are those created for the
    demo version of Magento on a standard 1.7 version.
    """

    def setUp(self):
        super(SetUpMagentoSynchronized, self).setUp()
        self.product_model = self.registry('product.product')
        self.mag_product_model = self.registry('magento.product.product')

    def add_product(self, name, sale_ok=True):
        return self.product_model.create(
            self.cr, self.uid, {
                'name': name,
                'sale_ok': sale_ok,
                })

    def active_product_autobind(self):
        self.backend_model.write(self.cr, self.uid, self.backend_id, {
            'auto_bind_product': True,
            })

    def unactive_product_autobind(self):
        self.backend_model.write(self.cr, self.uid, self.backend_id, {
            'auto_bind_product': False,
            })

    def get_product_binding(self, product_id):
        mag_product_model = self.registry('magento.product.product')
        return mag_product_model.search(self.cr, self.uid, [
            ('openerp_id', '=', product_id),
            ('backend_id', '=', self.backend_id),
            ])


class TestAutoBindProduct(SetUpProduct):

    def test_10_no_autobind(self):
        self.unactive_product_autobind()
        product_id = self.add_product('My product')
        binding_ids = self.get_product_binding(product_id)
        self.assertEqual(len(binding_ids), 0)

    def test_20_autobind(self):
        self.active_product_autobind()
        product_id = self.add_product('My product')
        binding_ids = self.get_product_binding(product_id)
        self.assertEqual(len(binding_ids), 1)

    def test_30_autobind_unactive_sale_ok(self):
        self.active_product_autobind()
        product_id = self.add_product('My product')
        self.product_model.write(self.cr, self.uid, [product_id], {
            'sale_ok': False,
            })
        binding_ids = self.get_product_binding(product_id)
        mag_product = self.mag_product_model.browse(
            self.cr, self.uid, binding_ids[0])
        self.assertEqual(mag_product.status, '2')

    def test_40_autobind_sale_ok_false(self):
        self.active_product_autobind()
        product_id = self.add_product('My product', False)
        binding_ids = self.get_product_binding(product_id)
        self.assertEqual(len(binding_ids), 0)

    def test_50_autobind_active_sale_ok(self):
        self.active_product_autobind()
        product_id = self.add_product('My product', False)
        self.product_model.write(self.cr, self.uid, [product_id], {
            'sale_ok': True,
            })
        binding_ids = self.get_product_binding(product_id)
        mag_product = self.mag_product_model.browse(
            self.cr, self.uid, binding_ids[0])
        self.assertEqual(mag_product.status, '1')


