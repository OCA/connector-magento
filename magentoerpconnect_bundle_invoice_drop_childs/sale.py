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
from openerp.osv import orm, fields

class sale_order_line(orm.Model):
    _inherit = 'sale.order.line'

    def _prepare_order_line_invoice_line(self, cr, uid, line, account_id=False, context=None):
        "Prevent creation of invoice lines for bundle child items"
        if line.bundle_parent_id and (line.price_subtotal <= 0.0):
            return {}
        return super(sale_order_line, self)._prepare_order_line_invoice_line(cr, uid, line, account_id=account_id, context=context)

    def _fnct_line_invoiced(self, cr, uid, ids, field_name, args, context=None):
        res = dict.fromkeys(ids, False)
        for this in self.browse(cr, uid, ids, context=context):
            if this.bundle_parent_id and (this.price_subtotal <= 0.0):
                parent_id = this.bundle_parent_id.id
                res[this.id] = super(sale_order_line, self)._fnct_line_invoiced(cr, uid, [parent_id], field_name, args, context=context)[parent_id]
            else:
                res[this.id] = super(sale_order_line, self)._fnct_line_invoiced(cr, uid, [this.id], field_name, args, context=context)[this.id]
        return res

    def _order_lines_from_invoice2(self, cr, uid, ids, context=None):
        # 'self' actually is an account.invoice, so super(sale_order_line, self) does not work
        return self.pool.get('sale.order.line')._order_lines_from_invoice(cr, uid, ids, context=context)

    _columns = {
        'invoiced': fields.function(_fnct_line_invoiced, string='Invoiced', type='boolean',
            store={
                'account.invoice': (_order_lines_from_invoice2, ['state'], 10),
                'sale.order.line': (lambda self, cr, uid, ids, ctx=None: ids, ['invoice_lines'], 10)}),
                }
