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

from osv import osv, fields
from tools.translate import _

class account_invoice(osv.osv):
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

    def create_magento_invoice(self, cr, uid, external_session, invoice_id, order_increment_id, context=None):
        item_qty = self.get_invoice_items(cr, uid, external_session, invoice_id, order_increment_id, context=context)
        try:
            return external_session.connection.call('sales_order_invoice.create', [order_increment_id,
                                                     item_qty, _('Invoice Created'), False, False])
        except Exception, e:
            external_session.logger.warning(_('Can not create the invoice for the order %s in the external system. Error : %s')%(order_increment_id, e))
        return False

    def ext_create(self, cr, uid, external_session, resources, mapping=None, mapping_id=None, context=None):
        ext_create_ids={}
        for resource_id, resource in resources.items():
            resource = resource[resource.keys()[0]]
            if resource['type'] == 'out_refund':
                method = "synoopenerpadapter_creditmemo.addInfo"
            elif resource['type'] == 'out_invoice':
                method = "synoopenerpadapter_invoice.addInfo"
            del resource['type']
            resource['reference'] = context.get('report_name')
            ext_create_ids[resource_id] = external_session.connection.call(method, 
                        [
                            resource['customer_id'],
                            resource['order_increment_id'],
                            resource['reference'],
                            resource['amount'],
                            resource['date'],
                            resource['customer_name'],
                        ])
            if resource['type'] == 'out_invoice':
                self.create_magento_invoice(cr, uid,  external_session, resource_id, 
                                                resource['order_increment_id'], context=context)
        return ext_create_ids




account_invoice()


class account_invoice_line(osv.osv):

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
account_invoice_line()
