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
import netsvc

DEBUG = True

#TODO, may be move that on out CSV mapping, but not sure we can easily
#see OpenERP sale/sale.py and Magento app/code/core/Mage/Sales/Model/Order.php for details
ORDER_STATUS_MAPPING = {'draft': 'processing', 'progress': 'processing', 'shipping_except': 'complete', 'invoice_except': 'complete', 'done': 'closed', 'cancel': 'canceled', 'waiting_date': 'holded'}

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
    
    def _get_exportable_root_category_ids(self, cr, uid, ids, prop, unknow_none, context):
        res = {}
        res1 = self._get_rootcategory(cr, uid, ids, prop, unknow_none, context)
        for shop in self.browse(cr, uid, ids, context):
            res[shop.id] = [res1[shop.id]]
        return res

    _columns = {
        'default_store_id':fields.integer('Magento Store ID'), #Many 2 one ?
        'website_id':fields.integer('Magento Website ID'), # Many 2 one ?
        'group_id':fields.integer('Magento ID'),
        'root_category_id':fields.integer('Root product Category'),
        'magento_root_category':fields.function(_get_rootcategory, type="many2one", relation="product.category", method=True, string="Root Category", store=True),
        'exportable_root_category_ids': fields.function(_get_exportable_root_category_ids, type="many2many", relation="product.category", method=True, string="Root Category"), #fields.function(_get_exportable_root_category_ids, type="many2one", relation="product.category", method=True, 'Exportable Root Categories'),
    }   

    def import_shop_orders(self, cr, uid, shop, defaults, ctx):#FIXME: no guest order support for now: [{'customer_id': {'nlike':False}}]
        magento_shop_id = self.oeid_to_extid(cr, uid, shop.id, shop.referential_id.id, context={})
        return self.pool.get('sale.order').mage_import_base(cr, uid, ctx.get('conn_obj', False), shop.referential_id.id,
                                                              defaults=defaults,
                                                              context={'one_by_one': True, 'ids_or_filter':[{'store_id': {'eq': magento_shop_id}, 'increment_id': {'gt': ctx.get('last_external_id', 0)}}]})

    def update_shop_orders(self, cr, uid, order, ext_id, ctx):
        conn = ctx.get('conn_obj', False)
        status = ORDER_STATUS_MAPPING.get(order.state, False)
        if status:
            return conn.call('sales_order.addComment', [ext_id, status, '', True])
        return True

sale_shop()


class sale_order(magerp_osv.magerp_osv):
    _inherit = "sale.order"
    
    def _auto_init(self, cr, context={}):
        cr.execute("ALTER TABLE sale_order_line ALTER COLUMN discount TYPE numeric(16,6);")
        super(sale_order, self)._auto_init(cr, context)
        
    def get_mage_customer_address_id(self, address_data):
        if address_data.get('customer_address_id', False):
            return {'customer_address_id': address_data['customer_address_id'], 'is_magento_order_address': False}
        else:
            return {'customer_address_id': 'mag_order' + str(address_data['address_id']), 'is_magento_order_address': True}
    
    def get_order_addresses(self, cr, uid, res, external_referential_id, data_record, key_field, mapping_lines, defaults, context):
        del(data_record['billing_address']['parent_id'])
        del(data_record['shipping_address']['parent_id'])
        
        #Magento uses to create same addresses over and over, try to detect if customer already have such an address (Magento won't tell it!)
        #We also create new addresses for each command here, passing a custom magento_id key in the following is what
        #avoid the base_external_referentials framework to try to update existing partner addresses
        data_record['billing_address'].update(self.get_mage_customer_address_id(data_record['billing_address']))
        data_record['shipping_address'].update(self.get_mage_customer_address_id(data_record['shipping_address']))
        shipping_default = {}
        billing_default = {}
        if res.get('parter_id', False):
            shipping_default = {'parter_id': res.get('parter_id', False)}
        billing_default = shipping_default.copy()
        billing_default.update({'email' : data_record.get('customer_email', False)})

        inv_res = self.pool.get('res.partner.address').ext_import(cr, uid, [data_record['billing_address']], 
                                                                  external_referential_id, billing_default, context)
        ship_res = self.pool.get('res.partner.address').ext_import(cr, uid, [data_record['shipping_address']], 
                                                                  external_referential_id, shipping_default, context)

        res['partner_order_id'] = len(inv_res['create_ids']) > 0 and inv_res['create_ids'][0] or inv_res['write_ids'][0]
        res['partner_invoice_id'] = res['partner_order_id']
        res['partner_shipping_id'] = (len(ship_res['create_ids']) > 0 and ship_res['create_ids'][0]) or (len(ship_res['write_ids']) > 0 and ship_res['write_ids'][0]) or res['partner_order_id'] #shipping might be the same as invoice address
        return res
    
    def get_order_lines(self, cr, uid, res, external_referential_id, data_record, key_field, mapping_lines, defaults, context):
        mapping_id = self.pool.get('external.mapping').search(cr,uid,[('model','=','sale.order.line'),('referential_id','=',external_referential_id)])
        if mapping_id:
            mapping_line_ids = self.pool.get('external.mapping.line').search(cr,uid,[('mapping_id','=',mapping_id),('type','in',['in_out','in'])])
            mapping_lines = self.pool.get('external.mapping.line').read(cr,uid,mapping_line_ids,['external_field','external_type','in_function'])
            if mapping_lines:
                lines_vals = []
                for line_data in data_record.get('items', []):
                    defaults_line = {'product_uom': 1}
                    #simple VAT tax on order line (else override method):
                    line_tax_vat = float(line_data['tax_percent']) / 100.0
                    if line_tax_vat > 0:
                        line_tax_ids = self.pool.get('account.tax').search(cr, uid, [('type_tax_use', '=', 'sale'), ('amount', '>=', line_tax_vat - 0.001), ('amount', '<=', line_tax_vat + 0.001)])
                        print "line_tax_ids", line_tax_ids
                        if line_tax_ids and len(line_tax_ids) > 0:
                            defaults_line['tax_id'] = [(6, 0, [line_tax_ids[0]])]
                    lines_vals.append((0, 0, self.oevals_from_extdata(cr, uid, external_referential_id, line_data, 'item_id', mapping_lines, defaults_line, context)))
                res['order_line'] = lines_vals
        return res
    
    def get_order_shipping(self, cr, uid, res, external_referential_id, data_record, key_field, mapping_lines, defaults, context):
        ship_product_id = self.pool.get('product.product').search(cr, uid, [('default_code', '=', 'SHIP MAGENTO')])[0]
        ship_product = self.pool.get('product.product').browse(cr, uid, ship_product_id, context)
        
        #simple VAT tax on shipping (else override method):
        ship_tax_vat = float(data_record['shipping_tax_amount'])/float(data_record['shipping_amount'])
        tax_id = []
        if ship_tax_vat > 0:
            ship_tax_ids = self.pool.get('account.tax').search(cr, uid, [('type_tax_use', '=', 'sale'), ('amount', '>=', ship_tax_vat - 0.001), ('amount', '<=', ship_tax_vat + 0.001)])
            if ship_tax_ids and len(ship_tax_ids) > 0:
                tax_id = [(6, 0, [ship_tax_ids[0]])]
        res['order_line'].append((0, 0, {
                                    'product_id': ship_product.id,
                                    'name': ship_product.name,
                                    'product_uom': ship_product.uom_id.id,
                                    'product_uom_qty': 1,
                                    'price_unit': float(data_record['shipping_amount']),
                                    'tax_id': tax_id
                                }))
        return res
    
    def oevals_from_extdata(self, cr, uid, external_referential_id, data_record, key_field, mapping_lines, defaults, context):
        res = super(magerp_osv.magerp_osv, self).oevals_from_extdata(cr, uid, external_referential_id, data_record, key_field, mapping_lines, defaults, context)

        if data_record.get('billing_address', False):
            res = self.get_order_addresses(cr, uid, res, external_referential_id, data_record, key_field, mapping_lines, defaults, context)
        if data_record.get('items', False):
            res = self.get_order_lines(cr, uid, res, external_referential_id, data_record, key_field, mapping_lines, defaults, context)
            if data_record.get('shipping_amount', False) and float(data_record.get('shipping_amount', False)) > 0:
                res = self.get_order_shipping(cr, uid, res, external_referential_id, data_record, key_field, mapping_lines, defaults, context)

        return res
    
    def ext_import(self, cr, uid, data, external_referential_id, defaults={}, context={}):
        res = super(sale_order, self).ext_import(cr, uid, data, external_referential_id, defaults, context)
        wf_service = netsvc.LocalService("workflow")
        for order in self.browse(cr, uid, res['create_ids'], context): #TODO complete!
            print order.shop_id.picking_generation_policy
            if order.order_policy == 'manual' and order.shop_id.picking_generation_policy != 'none':
                wf_service.trg_validate(uid, 'sale.order', order.id, 'order_confirm', cr)
                if order.shop_id.invoice_generation_policy != 'none':
                    wf_service.trg_validate(uid, 'sale.order', order.id, 'manual_invoice', cr)
            elif order.order_policy == 'picking' and order.shop_id.picking_generation_policy != 'none':
                wf_service.trg_validate(uid, 'sale.order', order.id, 'order_confirm', cr)
        return res

sale_order()
