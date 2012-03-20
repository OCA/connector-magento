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

from osv import osv, fields
from tools.translate import _


class sale_order(osv.osv):

    _inherit = 'sale.order'

    _columns = {'magento_ref': fields.char('Magento Invoice ID', size=32)}

    def magento_create_invoice(self, cr, uid, ids, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        for order in self.browse(cr, uid, ids, context=context):
            if not order.magento_incrementid:
                raise osv.except_osv(
                    _('Error'), _('This is not a Magento sale order.'))

            ctx = context.copy()
            ctx.update({
                'shop_id': order.shop_id.id,
                'external_referential_type':
                    order.shop_id.referential_id.type_id.name, })

            referential = order.shop_id.referential_id
            connection = referential.external_connection()
            external_invoice = self._create_external_invoice(
                cr, uid, order, connection, referential.id, context=ctx)
            self.write(
                cr, uid, order.id,
                {'magento_ref': external_invoice},
                context=context)
            cr.commit()

            self._check_need_to_update_single(
                cr, uid, order, connection, context=ctx)
        return True

    def _prepare_invoice(self, cr, uid, order, lines, context=None):
        """Prepare the dict of values to create the new invoice for a
           sale order. This method may be overridden to implement custom
           invoice generation (making sure to call super() to establish
           a clean extension chain).

           Inherited in order to:
           Update the Magento invoice id because the invoice has been
           created from the sale order and it is stored on the sale order
           first.

           :param browse_record order: sale.order record to invoice
           :param list(int) line: list of invoice line IDs that must be
                                  attached to the invoice
           :return: dict of value to create() the invoice
        """
        vals = super(sale_order, self)._prepare_invoice(
            cr, uid, order, lines, context=context)
        if order.magento_ref:
            vals['magento_ref'] = order.magento_ref
        return vals

sale_order()
