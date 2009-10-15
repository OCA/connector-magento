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
from magerp_core import Connection
#from base_external_referentials import external_osv

DEBUG = True

class sale_shop(magerp_osv.magerp_osv):
    _inherit = "sale.shop"
    
    def _get_website(self, cr, uid, ids, prop, unknow_none, context):
        res = self.website_get(cr, uid, ids, context={'field':'website_id'})
        return dict(res) 
   
    def _get_store(self, cr, uid, ids, prop, unknow_none, context):
        res = self.store_get(cr, uid, ids, context={'field':'default_store_id'})
        return dict(res)     

    def rootcategory_get(self, cr, uid, ids, context=None):
        if not len(ids):
            return []
        reads = self.read(cr, uid, ids, ['root_category_id', 'instance'], context)
        res = []
        for record in reads:
            if record['instance']:
                rid = self.pool.get('product.category').mage_to_oe(cr, uid, record['root_category_id'], record['instance'][0])
                res.append((record['id'], rid))
            else:
                res.append((record['id'], False))
        return res
    
    def _get_rootcategory(self, cr, uid, ids, prop, unknow_none, context):
        res = self.rootcategory_get(cr, uid, ids, context)
        return dict(res)     

    _columns = {
        'magento_id':fields.integer('ID'),
        'default_store_id':fields.integer('Store ID'), #Many 2 one ?
        'default_store':fields.function(_get_store, type="many2one", relation="magerp.storeviews", method=True, string="Store View"),
        'website_id':fields.integer('Website'), # Many 2 one ?
        'website':fields.function(_get_website, type="many2one", relation="external.shop.group", method=True, string="Website"),
        'root_category_id':fields.integer('Root product Category'),
        'root_category':fields.function(_get_rootcategory, type="many2one", relation="product.category", method=True, string="Root Category"),
        'instance':fields.many2one('external.referential', 'Instance', ondelete='cascade')
    }
    
    _defaults = {
        'payment_default_id': lambda *a: 1, #required field that would cause trouble if not set when importing
    }
    
    def export_products_collection(self, cr, uid, shop, exportable_products, ctx):
        attr_conn = Connection(shop.referential_id.location, shop.referential_id.apiusername, shop.referential_id.apipass, DEBUG)
        if attr_conn.connect():
            self.pool.get('product.product').mage_export(cr, uid, [product.id for product in exportable_products], attr_conn, shop.referential_id.id, DEBUG)
    
    #Return format of API:{'default_store_id': '1', 'group_id': '1', 'website_id': '1', 'name': 'Main Website Store', 'root_category_id': '2'
    
sale_shop()