# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2012 Camptocamp SA
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

import logging
from openerp.osv.orm import Model

_logger = logging.getLogger(__name__)

class product_product(Model):

    _inherit = 'product.product'

    def _magento_init_stock(self, cr, uid, product_id,
                            magento_id, connection, context=None):
        # initialize the inventory options on the created product
        shop = self.pool.get('sale.shop').browse(
            cr, uid, context['shop_id'], context=context)
        stock = shop.warehouse_id.lot_stock_id
        product = self.browse(cr, uid, product_id, context=context)
        stock_vals = self._prepare_inventory_magento_vals(
            cr, uid, product, stock, shop, context=context)

        connection.call('product_stock.update', [magento_id, stock_vals])
        _logger.info("Successfully initialized inventory "
                     "options on product with SKU %s " %
                     (product.magento_sku,))
        return True

    def ext_create(self, cr, uid, data, conn, method, oe_id, context):
        magento_product_id = super(product_product, self).ext_create(
            cr, uid, data, conn, method, oe_id, context)

        self._magento_init_stock(cr, uid, oe_id, magento_product_id,
                                 conn, context=context)
        return magento_product_id
