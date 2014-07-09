# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2014 Camptocamp SA
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

from openerp.addons.magentoerpconnect.unit.import_synchronizer import (
    import_record)
import openerp.tests.common as common
from .common import (mock_api,
                     mock_urlopen_image)
from .test_data import magento_base_responses
from .test_synchronization import SetUpMagentoSynchronized

DB = common.DB
ADMIN_USER_ID = common.ADMIN_USER_ID


class TestSaleOrder(SetUpMagentoSynchronized):

    def test_sale_order_copy_quotation(self):
        """ Copy a sales order with copy_quotation move bindings """
        backend_id = self.backend_id
        with mock_api(magento_base_responses):
            with mock_urlopen_image():
                import_record(self.session,
                              'magento.sale.order',
                              backend_id, 900000691)
        MagentoOrder = self.registry('magento.sale.order')
        MagentoLine = self.registry('magento.sale.order.line')
        SaleOrder = self.registry('sale.order')
        mag_order_ids = MagentoOrder.search(self.cr,
                                            self.uid,
                                            [('backend_id', '=', backend_id),
                                             ('magento_id', '=', '900000691')])
        self.assertEqual(len(mag_order_ids), 1)
        mag_order = MagentoOrder.browse(self.cr, self.uid, mag_order_ids[0])
        order = mag_order.openerp_id
        action = SaleOrder.copy_quotation(self.cr, self.uid, [order.id])
        new_id = action['res_id']
        order.refresh()
        self.assertFalse(order.magento_bind_ids)
        mag_order.refresh()
        self.assertEqual(mag_order.openerp_id.id, new_id)
        for mag_line in mag_order.magento_order_line_ids:
            self.assertEqual(mag_line.order_id.id, new_id)
