# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2014 initOS GmbH & Co. KG (<http://www.initos.com>).
#    Author Katja Matthes <katja.matthes at initos.com>
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
from openerp.osv import orm


class sale_order(orm.Model):
    _inherit = 'sale.order'

    def _create_pickings_and_procurements(self, cr, uid, order, order_lines,
                                          picking_id=False, context=None):
        """
        Override sale_stock module method to skip bundle products.
        """
        if context is None:
            context = {}
        lines_to_pick = []
        for line in order_lines:
            if line.has_bundle_children():
                continue
            lines_to_pick.append(line)

        return super(sale_order, self).\
            _create_pickings_and_procurements(cr, uid, order, lines_to_pick,
            picking_id=picking_id, context=context)

    def pickable_order_lines(self, cr, uid, ids, context=None):
        order_lines = super(sale_order, self).pickable_order_lines(cr, uid, ids, context=context)
        # We do not ship bundle products.
        return [l for l in order_lines
                if not l.has_bundle_children()]
        return order_lines
