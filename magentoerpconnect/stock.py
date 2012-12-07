# -*- encoding: utf-8 -*-
#########################################################################
#                                                                       #
#########################################################################
#                                                                       #
# Copyright (C) 2010 BEAU Sébastien                                     #
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

import xmlrpclib

from openerp.osv.orm import Model
from openerp.tools.translate import _
from base_sale_multichannels.sale import ExternalShippingCreateError

import logging
_logger = logging.getLogger(__name__)

class stock_picking(Model):

    _inherit = "stock.picking"

    def create_ext_complete_shipping(self, cr, uid, id, external_referential_id, magento_incrementid, mail_notification=True, context=None):
        if context is None: context = {}
        conn = context.get('conn_obj', False)
        ext_shipping_id = conn.call('sales_order_shipment.create', [magento_incrementid, {}, _("Shipping Created"), mail_notification, True])
        return ext_shipping_id

    def add_picking_line(self, cr, uid, lines, picking_line, context=None):
        """ A line to add in the shipping is a dict with : product_id and product_qty keys."""
        line_info = {'product_id': picking_line.product_id.id,
                     'product_qty': picking_line.product_qty,
        }
        lines.append(line_info)
        return lines

    def create_ext_partial_shipping(self, cr, uid, id, external_referential_id, magento_incrementid, mail_notification=True, context=None):
        if context is None: context = {}
        conn = context.get('conn_obj', False)
        ext_shipping_id = False
        order_items = conn.call('sales_order.info', [magento_incrementid])['items']
        product_2_item = {}
        for item in order_items:
            product_2_item.update({self.pool.get('product.product').get_oeid(cr, uid, item['product_id'], external_referential_id, context={}): item['item_id']})
        picking = self.pool.get('stock.picking').browse(cr, uid, id, context)
        item_qty = {}

        lines = []
        # get product and quantities to ship from the picking
        for line in picking.move_lines:
            lines = self.add_picking_line(cr, uid, lines, line, context)

        for line in lines:
            if item_qty.get(product_2_item[line['product_id']], False):
                item_qty[product_2_item[line['product_id']]] += line['product_qty']
            else:
                item_qty.update({product_2_item[line['product_id']]: line['product_qty']})

            ext_shipping_id = conn.call('sales_order_shipment.create', [magento_incrementid, item_qty, _("Shipping Created"), mail_notification, True])
        return ext_shipping_id

    def create_ext_shipping(self, cr, uid, id, picking_type, external_referential_id, context=None):
        """
        Create the shipping on Magento. It can be a partial or a complete shipment.

        :param str picking_type: 'partial' or 'complete'
        :return: the picking id on magento
        """
        sale = self.browse(cr, uid, id, context=context).sale_id
        magento_incrementid = sale.magento_incrementid
        carrier_id = self.read(cr, uid, id, ['carrier_id'], context)['carrier_id']
        if carrier_id:
            carrier_id = carrier_id[0]
            self.pool.get('delivery.carrier').check_ext_carrier_reference(cr, uid, carrier_id, magento_incrementid, context)

        ext_shipping_id = False
        meth = getattr(self, "create_ext_%s_shipping" % picking_type)
        try:
            ext_shipping_id = meth(
                cr, uid, id,
                external_referential_id,
                magento_incrementid,
                sale.shop_id.allow_magento_notification,
                context=context)
        except xmlrpclib.Fault, e:
            # When Magento is not able to create the shipping, it returns:
            # fault 102 is : <Fault 102: u"Impossible de faire l\'exp\xe9dition de la commande.">
            # In such case, we raise an ExternalShippingCreateError so
            # base_sale_multichannels will flag "do_not_export"
            # in order to exclude it from the future exports
            if e.faultCode == 102:
                raise ExternalShippingCreateError(e)

        if ext_shipping_id and carrier_id:
            self.add_ext_tracking_reference(cr, uid, id, carrier_id, ext_shipping_id, context)
        return ext_shipping_id

    def add_ext_tracking_reference(self, cr, uid, id, carrier_id, ext_shipping_id, context=None):
        if context is None: context = {}
        conn = context.get('conn_obj', False)
        carrier = self.pool.get('delivery.carrier').read(cr, uid, carrier_id, ['magento_carrier_code', 'magento_tracking_title'], context)

        if self.pool.get('ir.model.fields').search(cr, uid, [('name', '=', 'carrier_tracking_ref'), ('model', '=', 'stock.picking')]): #OpenERP v6 have the field carrier_tracking_ref on the stock_picking but v5 doesn't have it
            carrier_tracking_ref = self.read(cr, uid, id, ['carrier_tracking_ref'], context)['carrier_tracking_ref']
        else:
            carrier_tracking_ref = ''

        res = conn.call('sales_order_shipment.addTrack', [ext_shipping_id, carrier['magento_carrier_code'], carrier['magento_tracking_title'] or '', carrier_tracking_ref or ''])
        if res:
            _logger.info("Successfully adding a tracking reference to the shipping with OpenERP id %s and ext id %s in external sale system", id, ext_shipping_id)
        return True
