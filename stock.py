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

    def create_ext_complet_shipping(self, cr, uid, id, external_referential_id, ctx):
        conn = ctx.get('conn_obj', False)
        ext_shipping_id = False
        magento_incrementid = self.browse(cr, uid, id, ['sale_id'], ctx).sale_id.magento_incrementid
        carrier_id = self.pool.get('stock.picking').read(cr, uid, id, ['carrier_id'], ctx)['carrier_id']
        if carrier_id:
            carrier_id = carrier_id[0]
            self.pool.get('delivery.carrier').check_ext_carrier_reference(cr, uid, carrier_id, magento_incrementid, ctx)
        
        try:
            ext_shipping_id = conn.call('sales_order_shipment.create', [magento_incrementid, {}, _("Shipping Created"), True, True])
        except Exception, e:
            shipping_list = conn.call('sales_order_shipment.list')
            for shipping in shipping_list:
                if shipping['order_increment_id'] == magento_incrementid:
                    ext_shipping_id = shipping['increment_id']
                    break
        if ext_shipping_id and carrier_id:
            self.add_ext_tracking_reference(cr, uid, id, carrier_id, ext_shipping_id, ctx)
        return ext_shipping_id
        
        
    def create_ext_partial_shipping(self, cr, uid, id, external_referential_id, ctx):
        conn = ctx.get('conn_obj', False)
        ext_shipping_id = False
        magento_incrementid = self.browse(cr, uid, id, ['sale_id']).sale_id.magento_incrementid
        carrier_id = self.pool.get('stock.picking').read(cr, uid, id, ['carrier_id'], ctx)['carrier_id']
        if carrier_id:
            carrier_id = carrier_id[0]
            self.pool.get('delivery.carrier').check_ext_carrier_reference(cr, uid, carrier_id, magento_incrementid, ctx)
        
        order_items = conn.call('sales_order.info', [magento_incrementid])['items']
        product_2_item = {}
        for item in order_items:
            product_2_item.update({self.pool.get('product.product').extid_to_oeid(cr, uid, item['product_id'], external_referential_id, context={}): item['item_id']})
        
        picking = self.pool.get('stock.picking').browse(cr, uid, id, ctx)
        
        item_qty = {}
        for line in picking.move_lines:
            if item_qty.get(product_2_item[line.product_id.id], False):
                item_qty[product_2_item[line.product_id.id]] += line.product_qty
            else:
                item_qty.update({product_2_item[line.product_id.id]:line.product_qty})
        
        try:
            ext_shipping_id = conn.call('sales_order_shipment.create', [magento_incrementid, item_qty, _("Shipping Created"), True, True])
        except Exception, e:
            pass #TODO make sure that's because Magento picking already exists and then re-attach it or raise a error to re-attach manually!
        
        if ext_shipping_id and carrier_id:
            self.add_ext_tracking_reference(cr, uid, id, carrier_id, ext_shipping_id, ctx)
        return ext_shipping_id
        
        
    def add_ext_tracking_reference(self, cr, uid, id, carrier_id, ext_shipping_id, ctx):
        logger = netsvc.Logger()
        print 'add_ext_tracking_reference'
        conn = ctx.get('conn_obj', False)
        carrier = self.pool.get('delivery.carrier').read(cr, uid, carrier_id, ['magento_code', 'magento_tracking_title'], ctx)
        carrier_tracking_ref = self.read(cr, uid, id, ['carrier_tracking_ref'], ctx)['carrier_tracking_ref']
        
        res= conn.call('sales_order_shipment.addTrack', [ext_shipping_id, carrier['magento_code'], carrier['magento_tracking_title'] or '', carrier_tracking_ref or ''])
        if res:
            logger.notifyChannel('ext synchro', netsvc.LOG_INFO, "Successfully adding a tracking reference to the shipping with OpenERP id %s and ext id %s in external sale system" % (id, ext_shipping_id))       
        return True

stock_picking()

