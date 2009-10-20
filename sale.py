# -*- encoding: utf-8 -*-
#########################################################################
#                                                                       #
#########################################################################
#                                                                       #
# Copyright (C) 2009  Raphaël Valyi                                     #
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
import magerp_osv
#from base_external_referentials import external_osv

DEBUG = True

class sale_shop(magerp_osv.magerp_osv):
    _inherit = "sale.shop"
    
    def _shop_group_get(self, cr, uid, ids, prop, unknow_none, context):
        res = {}
        for shop in self.browse(cr, uid, ids, context):
            if shop.website_id:
                rid = self.pool.get('external.shop.group').extid_to_oeid(cr, uid, shop.website_id, shop.referential_id.id)
                res[shop.id] = rid
            else:
                res[shop.id] = False
        return res
  
    def _get_rootcategory(self, cr, uid, ids, prop, unknow_none, context):
        res = {}
        for shop in self.browse(cr, uid, ids, context):
            if shop.website_id:
                rid = self.pool.get('product.category').extid_to_oeid(cr, uid, shop.root_category_id, shop.referential_id.id)
                res[shop.id] = rid
            else:
                res[shop.id] = False
        return res

    _columns = {
        'default_store_id':fields.integer('Magento Store ID'), #Many 2 one ?
        'website_id':fields.integer('Magento Website ID'), # Many 2 one ?
        'group_id':fields.integer('Magento ID'),
        'root_category_id':fields.integer('Root product Category'),
        'root_category':fields.function(_get_rootcategory, type="many2one", relation="product.category", method=True, string="Root Category"),
    }
    
    _defaults = {
        'payment_default_id': lambda *a: 1, #required field that would cause trouble if not set when importing
    }


    def export_products_collection(self, cr, uid, shop, exportable_products, ext_connection, ctx):
        #TODO use new API!
        self.pool.get('product.product').mage_export(cr, uid, [product.id for product in exportable_products], ext_connection, shop.referential_id.id, DEBUG)


    def _get_pricelist(self, cr, uid, shop):
        if shop.pricelist_id:
            return shop.pricelist_id.id
        else:
            return self.pool.get('product.pricelist').search(cr, uid, [('type', '=', 'sale'), ('active', '=', True)])[0]
        

    def import_shop_orders(self, cr, uid, shop, ext_connection, ctx):
        result = self.pool.get('sale.order').mage_import_base(cr, uid, ext_connection, shop.referential_id.id, defaults={'pricelist_id':self._get_pricelist(cr, uid, shop), 'partner_id':1, 'partner_order_id':1, 'partner_invoice_id':1, 'partner_shipping_id':1})
        print "import_shop_orders RESULT",result
        #TODO store filter: sock.call(s,'sales_order.list',[{'order_id':{'gt':0},'store_id':{'eq':1}}])
    
sale_shop()


class sale_order(magerp_osv.magerp_osv):
    _inherit = "sale.order"
    
    _columns = {
        'magento_billing_address_id':fields.integer('Magento Billing Address ID'),
        'magento_shipping_address_id':fields.integer('Magento Billing Address ID'),
        'magento_customer_id':fields.integer('Magento Customer ID'),
    }
    
    def oevals_from_extdata(self, cr, uid, external_referential_id, data_record, key_field, mapping_lines, defaults, context):
        vals = super(magerp_osv.magerp_osv, self).oevals_from_extdata(cr, uid, external_referential_id, data_record, key_field, mapping_lines, defaults, context)
        return vals

sale_order()