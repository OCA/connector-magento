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
import xmlrpclib

from openerp.osv.orm import Model
from openerp.osv import fields
from openerp.osv.osv import except_osv
from tools.translate import _


class sale_order(Model):

    _inherit = 'sale.order'

    _columns = {'magento_ref': fields.char('Magento Invoice ID', size=32),
                'allow_magento_manual_invoice': fields.related(
                'base_payment_type_id', 'allow_magento_manual_invoice',
                type='boolean',
                string="Allow Manual Creation of Magento Invoice")}

    def _magento_create_invoice(self, cr, uid, order, context=None):
        shop = order.shop_id

        ctx = context.copy()
        ctx.update({
            'shop_id': shop.id,
            'external_referential_type':
                shop.referential_id.type_id.name, })

        referential = shop.referential_id
        connection = referential.external_connection()
        try:
            external_invoice = self._create_external_invoice(
                cr, uid, order, connection, referential.id, context=ctx)
        except xmlrpclib.Fault, magento_error:
            # TODO: in case of error on Magento because the invoice has
            # already been created, get the invoice number
            # and store it in magento_ref
            raise except_osv(_('Error'),
                             _("Error on Magento on the invoice creation "
                              "for order %s :\n%s") % (order.name, magento_error))
        self.write(
            cr, uid, order.id,
            {'magento_ref': external_invoice},
            context=context)
        cr.commit()

        self._check_need_to_update_single(
            cr, uid, order, connection, context=ctx)
        return True

    def button_magento_create_invoice(self, cr, uid, ids, context=None):
        order = self.browse(cr, uid, ids[0], context=context)
        if order.state != 'draft':
            raise except_osv(_('Error'),
                             _('This order is not a quotation.'))

        if not order.is_magento:
            raise except_osv(_('Error'),
                             _('This is not a Magento sale order.'))

        if not order.base_payment_type_id:
            raise except_osv(_('Error'),
                             _('This order has no external '
                               'payment type settings.'))

        if not order.base_payment_type_id.allow_magento_manual_invoice:
            raise except_osv(_('Error'),
                             _("Manual creation of the invoice on Magento "
                               "is forbidden for external payment : %s") %
                               order.ext_payment_method)

        # sale_exceptions module methods
        # in order to check if the order is valid
        # before create the invoice on magento
        # it maybe has something to correct
        exception_ids = self.detect_exceptions(
            cr, uid, [order.id], context=context)
        if exception_ids:
            return self._popup_exceptions(
                cr, uid, order.id,  context=context)

        self._magento_create_invoice(cr, uid, order, context=context)
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
           :param list(int) lines: list of invoice line IDs that must be
                                   attached to the invoice
           :return: dict of value to create() the invoice
        """
        vals = super(sale_order, self)._prepare_invoice(
            cr, uid, order, lines, context=context)
        if order.magento_ref:
            vals['magento_ref'] = order.magento_ref
        return vals
