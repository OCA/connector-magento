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

from openerp.osv.orm import Model
from openerp.osv import fields


class stock_picking(Model):
    _inherit = 'stock.picking'

    def create_ext_shipping(self, cr, uid, id, picking_type,
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


class stock_move(Model):
    _inherit = 'stock.move'
    _columns = {
        'sale_line_bundle_id': fields.many2one('sale.order.line',
                                               string='Sale Order Line Bundle')
        }
