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

from osv import fields,osv
from tools.translate import _
import netsvc

class stock_picking(osv.osv):
    _inherit = "stock.picking"


    def create_ext_complete_shipping(self, cr, uid, id, external_referential_id, magento_incrementid, context=None):
        if context is None: context = {}
        logger = netsvc.Logger()
        conn = context.get('conn_obj', False)
        ext_shipping_id = False
        try:
            ext_shipping_id = conn.call('sales_order_shipment.create', [magento_incrementid, {}, _("Shipping Created"), True, True])
        except Exception, e:
            logger.notifyChannel(_("Magento Call"), netsvc.LOG_ERROR, _("The picking from the order %s can't be created on Magento, please attach it manually, %s") % (magento_incrementid, e))
        return ext_shipping_id
    
    def add_picking_line(self, cr, uid, lines, picking_line, context=None):
        """ A line to add in the shipping is a dict with : product_id and product_qty keys."""
        line_info = {'product_id': picking_line.product_id.id,
                     'product_qty': picking_line.product_qty,
        }
        lines.append(line_info)
        return lines        


    def create_ext_partial_shipping(self, cr, uid, id, external_referential_id, magento_incrementid, context=None):
        if context is None: context = {}
        logger = netsvc.Logger()
        conn = context.get('conn_obj', False)
        ext_shipping_id = False
        order_items = conn.call('sales_order.info', [magento_incrementid])['items']
        product_2_item = {}
        for item in order_items:
            product_2_item.update({self.pool.get('product.product').extid_to_oeid(cr, uid, item['product_id'], external_referential_id, context={}): item['item_id']})
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
        try:
            ext_shipping_id = conn.call('sales_order_shipment.create', [magento_incrementid, item_qty, _("Shipping Created"), True, True])
        except Exception, e:
            logger.notifyChannel(_("Magento Call"), netsvc.LOG_ERROR, _("The picking from the order %s can't be created on Magento, please attach it manually, %s") % (magento_incrementid, e))
        return ext_shipping_id 


    def create_ext_shipping(self, cr, uid, id, picking_type, external_referential_id, context=None):
        magento_incrementid = self.browse(cr, uid, id, ['sale_id'], context).sale_id.magento_incrementid
        carrier_id = self.pool.get('stock.picking').read(cr, uid, id, ['carrier_id'], context)['carrier_id']
        if carrier_id:
            carrier_id = carrier_id[0]
            self.pool.get('delivery.carrier').check_ext_carrier_reference(cr, uid, carrier_id, magento_incrementid, context)

        ext_shipping_id = eval('self.create_ext_' + picking_type + '_shipping(cr, uid, id, external_referential_id, magento_incrementid, context)')

        if ext_shipping_id and carrier_id:
            self.add_ext_tracking_reference(cr, uid, id, carrier_id, ext_shipping_id, context)
        return ext_shipping_id


    def add_ext_tracking_reference(self, cr, uid, id, carrier_id, ext_shipping_id, context=None):
        if context is None: context = {}
        logger = netsvc.Logger()
        conn = context.get('conn_obj', False)
        carrier = self.pool.get('delivery.carrier').read(cr, uid, carrier_id, ['magento_code', 'magento_tracking_title'], context)
        
        if self.pool.get('ir.model.fields').search(cr, uid, [('name', '=', 'carrier_tracking_ref'), ('model', '=', 'stock.picking')]): #OpenERP v6 have the field carrier_tracking_ref on the stock_picking but v5 doesn't have it
            carrier_tracking_ref = self.read(cr, uid, id, ['carrier_tracking_ref'], context)['carrier_tracking_ref']
        else:
            carrier_tracking_ref = ''
            
        res= conn.call('sales_order_shipment.addTrack', [ext_shipping_id, carrier['magento_code'], carrier['magento_tracking_title'] or '', carrier_tracking_ref or ''])
        if res:
            logger.notifyChannel('ext synchro', netsvc.LOG_INFO, "Successfully adding a tracking reference to the shipping with OpenERP id %s and ext id %s in external sale system" % (id, ext_shipping_id))       
        return True

stock_picking()

