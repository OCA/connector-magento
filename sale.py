# -*- coding: utf-8 -*-
##############################################################################
#
#   Copyright (c) 2012 Camptocamp SA (http://www.camptocamp.com)
#   @author Guewen Baconnier
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

from osv import osv, fields


class sale_order(osv.osv):
    _inherit = "sale.order"

    def _merge_sub_items(self, cr, uid, product_type, top_item, child_items, context=None):
        """
        In the module magentoerpconnect_bundle_split, instead of merging the child items,
        we create a sale order line for each of them. As the bundle item price is the same
        as the sum of all the items, we set its price at 0.0

        :param top_item: main item (bundle, configurable)
        :param child_items: list of childs of the top item
        :return: list of items
        """
        if product_type == 'bundle':
            items = [child for child in child_items]
            bundle_item = top_item.copy()
            fields_to_zero = ['price', 'tax_amount', 'price_incl_tax',
                              'base_price', 'base_tax_amount', 'base_price_incl_tax',
                              'row_total', 'base_row_total']
            bundle_item.update(dict([(f, 0.0) for f in fields_to_zero]))
            items.insert(0, bundle_item)
            return items
        else:
            return super(sale_order, self)._merge_sub_items(cr, uid, product_type,
                                            top_item, child_items, context=context)

    def oe_create(self, cr, uid, vals, data, external_referential_id, defaults, context):
        order_id = super(sale_order, self).\
            oe_create(cr, uid, vals, data, external_referential_id, defaults, context)

        order = self.browse(cr, uid, order_id, context=context)

        bundle_ids = {}
        for line in order.order_line:
            if line.magento_parent_item_id:
                bundle_ids.setdefault(line.magento_parent_item_id, []).append(line.id)

        for parent_item_id, child_line_ids in bundle_ids.iteritems():
            parent_line_ids = self.search(cr, uid, [('magento_item_id', '=', parent_item_id)])
            if not parent_line_ids:
                continue
            self.write(cr, uid, child_line_ids,
                    {'bundle_parent_id': parent_line_ids[0]},
                       context=context)

        return order_id

sale_order()


class sale_order_line(osv.osv):

    _inherit = 'sale.order.line'

    _columns = {
        'bundle_parent_id': fields.many2one('sale.order.line', 'Bundle Line'),
        'magento_item_id': fields.integer('Magento Item ID'),
        'magento_parent_item_id': fields.integer('Magento Item ID'),
    }

sale_order_line()
