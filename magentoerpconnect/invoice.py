# -*- encoding: utf-8 -*-
#########################################################################
#This module intergrates Open ERP with the magento core                 #
#Core settings are stored here                                          #
#########################################################################
#                                                                       #
# Copyright (C) 2009  Sharoon Thomas, Raphaël Valyi                     #
# Copyright (C) 2011 Akretion Sébastien BEAU sebastien.beau@akretion.com#
#                                                                       #
#This program is free software: you can redistribute it and/or modify   #
#it under the terms of the GNU General Public License as published by   #
#the Free Software Foundation, either version 3 of the License, or      #
#(at your option) any later version.                                    #
#                                                                       #
#This program is distributed in the hope that it will be useful,        #
#but WITHOUT ANY WARRANTY; without even the implied warranty of         #
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the          #
#GNU General Public License for more details.                           #
#                                                                       #
#You should have received a copy of the GNU General Public License      #
#along with this program.  If not, see <http://www.gnu.org/licenses/>.  #
#########################################################################

from openerp.osv.orm import Model
from openerp.osv import fields
from openerp.tools.translate import _
from base_external_referentials.external_osv import ExternalSession
from openerp.osv.osv import except_osv

class account_invoice(Model):
    _inherit = "account.invoice"
    _columns = {
        'magento_ref':fields.char('Magento REF', size=32),
        }


    #TODO instead of calling again the sale order information
    # it will be better to store the ext_id of each sale order line
    #Moreover some code should be share between the partial export of picking and invoice
    def add_invoice_line(self, cr, uid, lines, line, context=None):
        """ A line to add in the invoice is a dict with : product_id and product_qty keys."""
        line_info = {'product_id': line.product_id.id,
                     'product_qty': line.quantity,
                     }
        lines.append(line_info)
        return lines

    def get_invoice_items(self, cr, uid, external_session, invoice_id, order_increment_id, context=None):
        invoice = self.browse(cr, uid, invoice_id, context=context)
        balance = invoice.sale_ids[0].amount_total - invoice.amount_total
        precision = self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')
        item_qty = {}
        if round(balance, precision):
            order_items = external_session.connection.call('sales_order.info', [order_increment_id])['items']
            product_2_item = {}
            for item in order_items:
                product_2_item.update({self.pool.get('product.product').get_oeid(cr, uid, item['product_id'],
                                        external_session.referential_id.id, context={}): item['item_id']})

            lines = []
            # get product and quantities to invoice from the invoice
            for line in invoice.invoice_line:
                lines = self.add_invoice_line(cr, uid, lines, line, context)

            for line in lines:
                #Only export product that exist in the original sale order
                if product_2_item.get(line['product_id']):
                    if item_qty.get(product_2_item[line['product_id']], False):
                        item_qty[product_2_item[line['product_id']]] += line['product_qty']
                    else:
                        item_qty.update({product_2_item[line['product_id']]: line['product_qty']})
        return item_qty

    def map_magento_order(self, cr, uid, external_session, invoice_id, order_increment_id, context=None):
        #TODO Error should be catch by the external report system (need some improvement before)
        #For now error are just logged into the OpenERP log file
        try:
            external_session.logger.warning('Try to map the invoice with an existing order')
            invoice_ids = external_session.connection.call('sales_order.get_invoice_ids', [order_increment_id])
            #TODO support mapping for partiel invoice if needed
            if len(invoice_ids) == 1:
                external_session.logger.info(
                    'Success to map the invoice %s with an existing order for the order %s.'
                    %(invoice_ids[0], order_increment_id))
                return invoice_ids[0]
            else:
                external_session.logger.error(
                    'Failed to map the invoice %s with an existing order for the order %s. Too many invoice found'
                    %(invoice_ids[0], order_increment_id))
                return False
        except Exception, e:
            external_session.logger.error(
                'Failed to map the invoice with an existing order for the order %s. Error : %s'
                %(order_increment_id, e))
        return False

    def create_magento_invoice(self, cr, uid, external_session, invoice_id, order_increment_id, context=None):
        item_qty = self.get_invoice_items(cr, uid, external_session, invoice_id, order_increment_id, context=context)
        try:
            return external_session.connection.call('sales_order_invoice.create', [order_increment_id,
                                                     item_qty, _('Invoice Created'), False, False])
        except Exception, e:
            external_session.logger.warning(
                'Can not create the invoice for the order %s in the external system. Error : %s'
                %(order_increment_id, e))
            invoice_id = self.map_magento_order(cr, uid, external_session, invoice_id, order_increment_id, context=context)
            if invoice_id:
                return invoice_id
            else:
                raise except_osv(_('Magento Error'), _('Failed to synchronize Magento invoice with OpenERP invoice'))

    def ext_create(self, cr, uid, external_session, resources, mapping=None, mapping_id=None, context=None):
        ext_create_ids={}
        for resource_id, resource in resources.items():
            res = self.ext_create_one_invoice(cr, uid, external_session, resource_id, resource, context=context)
            if res:
                ext_create_ids[resource_id] = res
        return ext_create_ids

    def ext_create_one_invoice(self, cr, uid, external_session, resource_id, resource, context=None):
        resource = resource[resource.keys()[0]]
        if resource['type'] == 'out_invoice':
            return self.create_magento_invoice(cr, uid, external_session,
                                resource_id, resource['order_increment_id'], context=context)
        return False

    def _export_one_invoice(self, cr, uid, invoice, context=None):
        if invoice.sale_ids:
            sale = invoice.sale_ids[0]
            referential = sale.shop_id.referential_id
            if referential and referential.type_name == 'Magento':
                ext_id = invoice.get_extid(referential.id)
                if ext_id:
                    return ext_id
                else:
                    external_session = ExternalSession(referential, sale.shop_id)
                    return self._export_one_resource(cr, uid, external_session, invoice.id,
                                                     context=context)

    def export_invoice(self, cr, uid, ids, context=None):
        for invoice in self .browse(cr, uid, ids, context=context):
            self._export_one_invoice(cr, uid, invoice, context=context)
        return True


class account_invoice_line(Model):
    _inherit = 'account.invoice.line'
    _columns = {
        # Forced the precision of the account.invoice.line discount field
        # to 3 digits in order to be able to have the same amount as Magento.
        # Example: Magento has a sale line of 299€ and 150€ of discount, so a line at 149€.
        # We translate it to a percent in the openerp invoice line
        # With a 2 digits precision, we can have 50.17 % => 148.99 or 50.16% => 149.02.
        # Force the digits to 3 allows to have 50.167% => 149€
        'discount': fields.float('Discount (%)', digits=(16, 3)),
        }
