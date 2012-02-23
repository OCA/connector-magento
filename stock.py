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


class stock_picking(osv.osv):

    _inherit = 'stock.picking'

    def create_ext_shipping(self, cr, uid, id,picking_type,
                            external_referential_id, context):
        """
        Create the shipping on Magento. It can be a partial
         or a complete shipment.

        Always proceed with a complete shipment of the picking
        contains bundle items.
        As it may be possible to manage partial with bundle,
        it is complex because Magento wait for the bundle item
        and not the sub-items.
        We'll have issue with a second packing which
        contains only bundle items as instance.
        In the implementation of this module,
        they anyway have only full shipments.

        :param str picking_type: 'partial' or 'complete'
        :return: the picking id on magento
        """

        picking = self.browse(cr, uid, id, context=context)
        for line in picking.move_lines:
            if line.sale_line_bundle_id:
                picking_type = 'complete'
                break

        return super(stock_picking, self).create_ext_shipping(
            cr, uid, id, picking_type,
            external_referential_id, context)

stock_picking()


class stock_move(osv.osv):

    _inherit = 'stock.move'

    _columns = {
        'sale_line_bundle_id': fields.many2one('sale.order.line',
                                               string='Sale Order Line Bundle')
    }

stock_move()
