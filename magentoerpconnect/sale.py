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
from tools.translate import _
import string
#from datetime import datetime
import tools
import time
DEBUG = True

#TODO, may be move that on out CSV mapping, but not sure we can easily
#see OpenERP sale/sale.py and Magento app/code/core/Mage/Sales/Model/Order.php for details
ORDER_STATUS_MAPPING = {'draft': 'processing', 'progress': 'processing', 'shipping_except': 'complete', 'invoice_except': 'complete', 'done': 'closed', 'cancel': 'canceled', 'waiting_date': 'holded'}
SALE_ORDER_MAPPING = {} #{1: 100000001, 3: 300000001, 2: 200000001} #Usefull for first import if there is a lot of sale orders! IMPORTANT : Note that this is template, we just let it here for example, working with magento's example data. 
SALE_ORDER_IMPORT_STEP = 200

class sale_shop(magerp_osv.magerp_osv):
    _inherit = "sale.shop"
    
    def _get_exportable_product_ids(self, cr, uid, ids, name, args, context=None):
        res = super(sale_shop, self)._get_exportable_product_ids(cr, uid, ids, name, args, context=None)
        for shop_id in res:
            website_id =  self.read(cr, uid, shop_id, ['shop_group_id'])
            if website_id.get('shop_group_id', False):
                res[shop_id] = self.pool.get('product.product').search(cr, uid, [('magento_exportable', '=', True), ('id', 'in', res[shop_id]), "|", ('websites_ids', 'in', [website_id['shop_group_id'][0]]) , ('websites_ids', '=', False)])
            else:
                res[shop_id] = []
        return res

    def _get_default_storeview_id(self, cr, uid, ids, prop, unknow_none, context):
        res = {}
        for shop in self.browse(cr, uid, ids, context):
            if shop.default_storeview_integer_id:
                rid = self.pool.get('magerp.storeviews').extid_to_oeid(cr, uid, shop.default_storeview_integer_id, shop.referential_id.id)
                res[shop.id] = rid
            else:
                res[shop.id] = False
        return res
    
    def export_images(self, cr, uid, ids, context):
        logger = netsvc.Logger()
        start_date = time.strftime('%Y-%m-%d %H:%M:%S')
        image_obj = self.pool.get('product.images')
        for shop in self.browse(cr, uid, ids):
            context['shop_id'] = shop.id
            context['external_referential_id'] = shop.referential_id.id
            context['conn_obj'] = self.external_connection(cr, uid, shop.referential_id)
            context['last_images_export_date'] = shop.last_images_export_date
            exportable_product_ids = self.read(cr, uid, shop.id, ['exportable_product_ids'], context=context)['exportable_product_ids']
            res = self.pool.get('product.product').get_exportable_images(cr, uid, exportable_product_ids, context=context)
            if res:
                logger.notifyChannel('ext synchro', netsvc.LOG_INFO, "Creating %s images" %(len(res['to_create'])))
                logger.notifyChannel('ext synchro', netsvc.LOG_INFO, "Updating %s images" %(len(res['to_update'])))
                image_obj.update_remote_images(cr, uid, res['to_update']+res['to_create'], context)
            self.write(cr,uid,context['shop_id'],{'last_images_export_date': start_date})
        return True
               
  
    def _get_rootcategory(self, cr, uid, ids, prop, unknow_none, context):
        res = {}
        for shop in self.browse(cr, uid, ids, context):
            if shop.root_category_id:
                rid = self.pool.get('product.category').extid_to_oeid(cr, uid, shop.root_category_id, shop.referential_id.id)
                res[shop.id] = rid
            else:
                res[shop.id] = False
        return res

    def _set_rootcategory(self, cr, uid, id, name, value, fnct_inv_arg, context):
        res = {}
        ir_model_data_obj = self.pool.get('ir.model.data')
        shop = self.browse(cr, uid, id, context=context)
        if shop.root_category_id:
            model_data_id = ir_model_data_obj.search(cr, uid, [('name', '=', 'product.category_'+ str(shop.root_category_id)), ('model', '=', 'product.category'), ('external_referential_id', '=', shop.referential_id.id)])
            if len(model_data_id) == 1:
                ir_model_data_obj.write(cr, uid, model_data_id, {'res_id' : value}, context=context)
            elif len(model_data_id) == 0:
                raise osv.except_osv(_('Warning!'), _('No external id found, are you sure that the referential are syncronized? Please contact your administrator. (more information in magentoerpconnect/sale.py)'))
            else:
                raise osv.except_osv(_('Warning!'), _('You have an error in the ir_model_data table, please contact your administrator. (more information in magentoerpconnect/sale.py)'))
        return True

    def _get_exportable_root_category_ids(self, cr, uid, ids, prop, unknow_none, context):
        res = {}
        res1 = self._get_rootcategory(cr, uid, ids, prop, unknow_none, context)
        for shop in self.browse(cr, uid, ids, context):
            res[shop.id] = res1[shop.id] and [res1[shop.id]] or []
        return res

    _columns = {
        'default_storeview_integer_id':fields.integer('Magento default Storeview ID'), #This field can't be a many2one because store field will be mapped before creating storeviews
        'default_storeview_id':fields.function(_get_default_storeview_id, type="many2one", relation="magerp.storeviews", method=True, string="Default Storeview"),
        'root_category_id':fields.integer('Root product Category'), #This field can't be a many2one because store field will be mapped before creating category
        'magento_root_category':fields.function(_get_rootcategory, fnct_inv = _set_rootcategory, type="many2one", relation="product.category", method=True, string="Root Category", store=True),
        'exportable_root_category_ids': fields.function(_get_exportable_root_category_ids, type="many2many", relation="product.category", method=True, string="Root Category"), #fields.function(_get_exportable_root_category_ids, type="many2one", relation="product.category", method=True, 'Exportable Root Categories'),
        'storeview_ids': fields.one2many('magerp.storeviews', 'shop_id', 'Store Views'),
        'exportable_product_ids': fields.function(_get_exportable_product_ids, method=True, type='one2many', relation="product.product", string='Exportable Products'),
        'magento_shop': fields.boolean('Magento Shop', readonly=True),
        'auto_import': fields.boolean('Automatic Import'),
        'allow_magento_order_status_push': fields.boolean('Allow Magento Order Status push', help='Allow to send back order status to Magento if order status changed in OpenERP first?'),
        'allow_magento_notification': fields.boolean('Allow Magento Notification', help='Allow Magento to notify customer (mail) if OpenERP update Magento order status?'),
    }   

    _defaults = {
        'auto_import': lambda * a: True,
        'allow_magento_order_status_push': lambda * a: False,
        'allow_magento_notification': lambda * a: False,
    }


    def import_shop_orders(self, cr, uid, shop, defaults, context):
        result = []
        for storeview in shop.storeview_ids:
            magento_storeview_id = self.pool.get('magerp.storeviews').oeid_to_extid(cr, uid, storeview.id, shop.referential_id.id, context={})
            ids_or_filter = [{'store_id': {'eq': magento_storeview_id}, 'state': {'neq': 'canceled'}}]
            res = {'create_ids': [], 'write_ids': []}
            nb_last_created_ids = SALE_ORDER_IMPORT_STEP
            while nb_last_created_ids != 0:
                #get last imported order:
                last_external_id = self.get_last_imported_external_id(cr, 'sale.order', shop.referential_id.id, "sale_order.shop_id=%s and magento_storeview_id=%s" % (shop.id, storeview.id))[1]
                if last_external_id:
                    ids_or_filter[0]['increment_id'] = {'from': int(last_external_id) + 1, 'to': int(last_external_id) + SALE_ORDER_IMPORT_STEP}
                else:
                    if SALE_ORDER_MAPPING.get(magento_storeview_id, False):
                        ids_or_filter[0]['increment_id'] = {'lt': SALE_ORDER_MAPPING[magento_storeview_id] + SALE_ORDER_IMPORT_STEP}
                defaults['magento_storeview_id'] = storeview.id
                resp = self.pool.get('sale.order').mage_import_base(cr, uid, context.get('conn_obj', False), shop.referential_id.id, defaults=defaults, context={'one_by_one': True, 'ids_or_filter':ids_or_filter})
                res['create_ids'] += resp['create_ids']
                res['write_ids'] += resp['write_ids']
                nb_last_created_ids = len(resp['create_ids'])
            result.append(res)
        return result
        
    def update_orders(self, cr, uid, ids, context=None):
        # First update the shop order from OERP
        super(sale_shop, self).update_orders(cr,uid,ids,context)
        logger = netsvc.Logger()
        so_obj = self.pool.get('sale.order')

        for shop in self.browse(cr, uid, ids):
            conn = self.external_connection(cr, uid, shop.referential_id)
            # Update the state of orders in OERP that are in "need_to_update":True
            # from the Magento's corresponding orders
    
            # Get all need_to_update orders in OERP
            orders_to_update = so_obj.search(cr,uid,[('need_to_update', '=', True), ('shop_id', '=', shop.id)])
            for order in so_obj.browse(cr, uid, orders_to_update):
                mag_status = ORDER_STATUS_MAPPING.get(order.state, False)
                # For each one, check if the status has change in Magento
                # We dont use oeid_to_extid function cause it only handle int id
                # Magento can have something like '100000077-2'
                model_data_ids = self.pool.get('ir.model.data').search(cr, uid, [('model', '=', so_obj._name), ('res_id', '=', order.id), ('external_referential_id', '=', shop.referential_id.id)])
                if model_data_ids:
                    prefixed_id = self.pool.get('ir.model.data').read(cr, uid, model_data_ids[0], ['name'])['name']
                    ext_id = so_obj.id_from_prefixed_id(prefixed_id)
                else:
                    return False
                data_record=conn.call('sales_order.info', [ext_id])
                updated = False
                if data_record['status'] == 'canceled':
                    wf_service = netsvc.LocalService("workflow")
                    wf_service.trg_validate(uid, 'sale.order', order.id, 'cancel', cr)
                    updated = True
                    self.log(cr, uid, order.id, "order %s canceled when updated from external system" % (order.id,))
                    logger.notifyChannel('ext synchro', netsvc.LOG_INFO, "order %s canceled when updated from external system" % (order.id,))
                # If the order isn't canceled and was blocked, 
                # so we follow the standard flow according to ext_payment_method:
                else:
                    paid = so_obj.create_payments(cr, uid, data_record, order.id, context)                        
                    so_obj.oe_status(cr, uid, order.id, paid, context)
                    updated = paid
                    if paid:
                        self.log(cr, uid, order.id, "order %s paid when updated from external system" % (order.id,))
                        logger.notifyChannel('ext synchro', netsvc.LOG_INFO, "order %s paid when updated from external system" % (order.id,))
                # Untick the need_to_update if updated (if so was canceled in magento
                # or if it has been paid through magento)
                if updated:
                    so_obj.write(cr, uid, order.id, {'need_to_update': False})
                cr.commit();
        return False
         
    def update_shop_orders(self, cr, uid, order, ext_id, context):
        result = {}

        if order.shop_id.allow_magento_order_status_push:        
            #status update:
            conn = context.get('conn_obj', False)
            logger = netsvc.Logger()
            status = ORDER_STATUS_MAPPING.get(order.state, False)
            if status:
                result['status_change'] = conn.call('sales_order.addComment', [ext_id, status, '', order.shop_id.allow_magento_notification])
                # If status has changed into OERP and the order need_to_update, then we consider the update is done
                # remove the 'need_to_update': True
                if order.need_to_update:
                    self.pool.get('sale.order').write(cr, uid, order.id, {'need_to_update': False})
        
            #creation of Magento invoice eventually:
            cr.execute("select account_invoice.id from account_invoice inner join sale_order_invoice_rel on invoice_id = account_invoice.id where order_id = %s" % order.id)
            resultset = cr.fetchone()
            if resultset and len(resultset) == 1:
                invoice = self.pool.get("account.invoice").browse(cr, uid, resultset[0])
                if invoice.amount_total == order.amount_total and not invoice.magento_ref:
                    try:
                        result['magento_invoice_ref'] = conn.call('sales_order_invoice.create', [order.magento_incrementid, [], _("Invoice Created"), True, order.shop_id.allow_magento_notification])
                        self.pool.get("account.invoice").write(cr, uid, invoice.id, {'magento_ref': result['magento_invoice_ref'], 'origin': result['magento_invoice_ref']})
                        self.log(cr, uid, order.id, "created Magento invoice for order %s" % (order.id,))
                    except Exception, e:
                        self.log(cr, uid, order.id, "failed to create Magento invoice for order %s" % (order.id,))
                        logger.notifyChannel('ext synchro', netsvc.LOG_DEBUG, "failed to create Magento invoice for order %s" % (order.id,))
                        #TODO make sure that's because Magento invoice already exists and then re-attach it!

        return result



    def _sale_shop(self, cr, uid, callback, context=None):
        if context is None:
            context = {}
        proxy = self.pool.get('sale.shop')
        domain = [ ('magento_shop', '=', True), ('auto_import', '=', True) ]

        ids = proxy.search(cr, uid, domain, context=context)
        if ids:
            callback(cr, uid, ids, context=context)

        tools.debug(callback)
        tools.debug(ids)
        return True

    # Schedules functions ============ #
    def run_import_orders_scheduler(self, cr, uid, context=None):
        self._sale_shop(cr, uid, self.import_orders, context=context)

    def run_update_orders_scheduler(self, cr, uid, context=None):
        self._sale_shop(cr, uid, self.update_orders, context=context)

    def run_export_catalog_scheduler(self, cr, uid, context=None):
        self._sale_shop(cr, uid, self.export_catalog, context=context)

    def run_export_stock_levels_scheduler(self, cr, uid, context=None):
        self._sale_shop(cr, uid, self.export_inventory, context=context)

    def run_update_images_scheduler(self, cr, uid, context=None):
        self._sale_shop(cr, uid, self.export_images, context=context)
                   
    def run_export_shipping_scheduler(self, cr, uid, context=None):
        self._sale_shop(cr, uid, self.export_shipping, context=context)

sale_shop()


class sale_order(magerp_osv.magerp_osv):
    _inherit = "sale.order"
    
    _columns = {
                'magento_incrementid': fields.char('Magento Increment ID', size=32),
                'magento_storeview_id': fields.many2one('magerp.storeviews', 'Magento Store View'),
    }
    
    def _auto_init(self, cr, context=None):
        cr.execute("ALTER TABLE sale_order_line ALTER COLUMN discount TYPE numeric(16,6);")
        cr.execute("ALTER TABLE account_invoice_line ALTER COLUMN discount TYPE numeric(16,6);")
        super(sale_order, self)._auto_init(cr, context)
        
    def get_mage_customer_address_id(self, address_data):
        if address_data.get('customer_address_id', False):
            return {'customer_address_id': address_data['customer_address_id'], 'is_magento_order_address': False}
        else:
            return {'customer_address_id': 'mag_order' + str(address_data['address_id']), 'is_magento_order_address': True}
    
    def get_order_addresses(self, cr, uid, res, external_referential_id, data_record, key_field, mapping_lines, defaults, context):
        partner_obj = self.pool.get('res.partner')
        partner_address_obj = self.pool.get('res.partner.address')
        del(data_record['billing_address']['parent_id'])
        if 'parent_id' in data_record['shipping_address']:
            del(data_record['shipping_address']['parent_id'])
        
        #Magento uses to create same addresses over and over, try to detect if customer already have such an address (Magento won't tell it!)
        #We also create new addresses for each command here, passing a custom magento_id key in the following is what
        #avoid the base_external_referentials framework to try to update existing partner addresses
        data_record['billing_address'].update(self.get_mage_customer_address_id(data_record['billing_address']))
        if 'address_type' in data_record['shipping_address']:
            data_record['shipping_address'].update(self.get_mage_customer_address_id(data_record['shipping_address']))
        shipping_default = {}
        billing_default = {}
        res['partner_id'] = self.pool.get('res.partner').extid_to_oeid(cr, uid, data_record['customer_id'], external_referential_id)
        if res.get('partner_id', False):
            shipping_default = {'partner_id': res.get('partner_id', False)}
        billing_default = shipping_default.copy()
        billing_default.update({'email' : data_record.get('customer_email', False)})

        inv_res = partner_address_obj.ext_import(cr, uid, [data_record['billing_address']], external_referential_id, billing_default, context)
        if 'address_type' in data_record['shipping_address']:
            ship_res = partner_address_obj.ext_import(cr, uid, [data_record['shipping_address']], external_referential_id, shipping_default, context)
        else:
            ship_res = partner_address_obj.ext_import(cr, uid, [data_record['billing_address']], external_referential_id, shipping_default, context)

        res['partner_order_id'] = len(inv_res['create_ids']) > 0 and inv_res['create_ids'][0] or inv_res['write_ids'][0]
        res['partner_invoice_id'] = res['partner_order_id']
        res['partner_shipping_id'] = (len(ship_res['create_ids']) > 0 and ship_res['create_ids'][0]) or (len(ship_res['write_ids']) > 0 and ship_res['write_ids'][0]) or res['partner_order_id'] #shipping might be the same as invoice address
        
        result = partner_address_obj.read(cr, uid, res['partner_order_id'], ['partner_id'])
        if result and result['partner_id']:
            partner_id = result['partner_id'][0]
        else: #seems like a guest order, create partner on the fly from billing address to make OpenERP happy:
            #TODO fix the bug in magento, indeed some order have as value for the customer_id : None. It's why we create a customer on the fly, with this method some parameter are maybe not mapped, be careful
            vals = {}
            store_id = self.pool.get('magerp.storeviews').extid_to_oeid(cr, uid, data_record['store_id'], external_referential_id)
            if store_id:
		        lang = self.pool.get('magerp.storeviews').browse(cr, uid, store_id).lang_id
		        vals.update({'store_id' : store_id, 'lang' : lang and lang.code or False})
            vals.update({'name': data_record['billing_address'].get('lastname', '') + ' ' + data_record['billing_address'].get('firstname', '')})
            partner_id = partner_obj.create(cr, uid, vals, context)
            partner_address_obj.write(cr, uid, [res['partner_order_id'], res['partner_invoice_id'], res['partner_shipping_id']], {'partner_id': partner_id})
        res['partner_id'] = partner_id

        # Adds last store view (m2o field store_id) to the list of store views (m2m field store_ids)
        partner = partner_obj.browse(cr, uid, partner_id)
        if partner.store_id:
            store_ids = [store.id for store in partner.store_ids]
            if partner.store_id.id not in store_ids:
                store_ids.append(partner.store_id.id)
            partner_obj.write(cr, uid, [partner_id], {'store_ids': [(6,0,store_ids)]})

        # Adds vat number (country code+magento vat) if base_vat module is installed and Magento sends customer_taxvat
        cr.execute('select * from ir_module_module where name=%s and state=%s', ('base_vat','installed'))
        if cr.fetchone() and 'customer_taxvat' in data_record and data_record['customer_taxvat']:
            allchars = string.maketrans('', '')
            delchars = ''.join([c for c in allchars if c not in string.letters + string.digits])
            vat = data_record['customer_taxvat'].translate(allchars, delchars).upper()
            vat_country, vat_number = vat[:2].lower(), vat[2:]
            check = getattr(partner_obj, 'check_vat_' + vat_country)
            vat_ok = check(vat_number)
            if not vat_ok and 'country_id' in data_record['billing_address']:
                # Maybe magento vat number has not country code prefix. Take it from billing address.
                check = getattr(partner_obj, 'check_vat_' + data_record['billing_address']['country_id'].lower())
                vat_ok = check(vat)
                vat = data_record['billing_address']['country_id'] + vat
            if vat_ok:    
                partner_obj.write(cr, uid, [partner_id], {'vat_subjected':True, 'vat':vat})
        return res
    
    def get_order_lines(self, cr, uid, res, external_referential_id, data_record, key_field, mapping_lines, defaults, context):
        mapping_id = self.pool.get('external.mapping').search(cr,uid,[('model','=','sale.order.line'),('referential_id','=',external_referential_id)])
        if mapping_id:
            mapping_line_ids = self.pool.get('external.mapping.line').search(cr,uid,[('mapping_id','=',mapping_id),('type','in',['in_out','in'])])
            mapping_lines = self.pool.get('external.mapping.line').read(cr,uid,mapping_line_ids,['external_field','external_type','in_function'])
            if mapping_lines:
                lines_vals = []
                is_tax_included = defaults.get('price_type', False) == 'tax_included'
                for line_data in data_record.get('items', []):
                    # Setting the UoM in sale order line as defined in product definition in openerp
                    product_id = self.pool.get('product.product').extid_to_oeid(cr, uid, line_data['product_id'], external_referential_id)
                    product = self.pool.get('product.product').browse(cr, uid, product_id)
                    defaults_line = {'product_uom': product.uom_id.id}
                    #simple VAT tax on order line (else override method):
                    line_tax_vat = float(line_data['tax_percent']) / 100.0
                    if line_tax_vat > 0:
                        line_tax_ids = self.pool.get('account.tax').search(cr, uid, ['|', ('type_tax_use', '=', 'all'), ('type_tax_use', '=', 'sale'), ('price_include', '=', is_tax_included), ('amount', '>=', line_tax_vat - 0.001), ('amount', '<=', line_tax_vat + 0.001)])
                        if line_tax_ids and len(line_tax_ids) > 0:
                            defaults_line['tax_id'] = [(6, 0, [line_tax_ids[0]])]
                    context.update({'partner_id': res['partner_id'], 'pricelist_id': res['pricelist_id']})
                    if defaults.get('price_type', False) == 'tax_included':
                        context.update({'price_is_tax_included': True})
                    line_val = self.oevals_from_extdata(cr, uid, external_referential_id, line_data, 'item_id', mapping_lines, defaults_line, context)
                                        
                    if line_val['product_id']:
                        line_val['type'] = self.pool.get('product.product').read(cr, uid, line_val['product_id'], ['procure_method'], context)['procure_method']
                    if not line_val.has_key('_CANCEL_IMPORT'):
                        lines_vals.append((0, 0, line_val))
                res['order_line'] = lines_vals
        return res


    def add_order_extra_line(self, cr, uid, res, data_record, ext_field, product_code, context):
        """ Add or substract amount on order as a separate line item with single quantity for each type of amounts like :
        shipping, cash on delivery, discount, gift certificates...
        Arguments :
        ext_field: name of the field in data_record where the amount is stored
        product_code: code of the product to use in the sale order line
        Optional arguments in kwargs:
        sign: multiply the amount with the sign to add or substract it from the sale order
        ext_tax_field: name of the field in data_record where the tax amount is stored
        ext_code_field: name of the field in data_record containing a code (for coupons and gift certificates) which will be printed on the product name
        """
        sign = 'sign' in context and context['sign'] or 1
        ext_tax_field = 'ext_tax_field' in context and context['ext_tax_field'] or None
        ext_code_field = 'ext_code_field' in context and context['ext_code_field'] or None

        product_id = self.pool.get('product.product').search(cr, uid, [('default_code', '=', product_code)])[0]
        product = self.pool.get('product.product').browse(cr, uid, product_id, context)
        is_tax_included = defaults.get('price_type', False) == 'tax_included'
        amount = float(data_record[ext_field]) * sign
        tax_id = []
        if ext_tax_field:
            if data_record[ext_tax_field] and float(data_record[ext_tax_field]) != 0:
                tax_vat = abs(float(data_record[ext_tax_field]) / amount)
                tax_ids = self.pool.get('account.tax').search(cr, uid, [('price_include', '=', is_tax_included), ('type_tax_use', '=', 'sale'), ('amount', '>=', tax_vat - 0.001), ('amount', '<=', tax_vat + 0.001)])
                if tax_ids and len(tax_ids) > 0:
                    tax_id = [(6, 0, [tax_ids[0]])]
            else:
                #try to find a tax with less precision 
                tax_ids = self.pool.get('account.tax').search(cr, uid, [('price_include', '=', is_tax_included), ('type_tax_use', '=', 'sale'), ('amount', '>=', tax_vat - 0.01), ('amount', '<=', tax_vat + 0.01)])
                if tax_ids and len(tax_ids) > 0:
                    tax_id = [(6, 0, [tax_ids[0]])]

        name = product.name
        if ext_code_field and data_record.get(ext_code_field, False):
            name = "%s [%s]" % (name, data_record[ext_code_field])
		
        if is_tax_included:
            price_unit = float(amount) + float(data_record[ext_tax_field])
        else:
            price_unit = float(amount)

        res['order_line'].append((0, 0, {
                                    'product_id': product.id,
                                    'name': name,
                                    'product_uom': product.uom_id.id,
                                    'product_uom_qty': 1,
                                    'price_unit': price_unit,
                                    'tax_id': tax_id
                                }))
        return res
    
    def add_order_shipping(self, cr, uid, res, external_referential_id, data_record, key_field, mapping_lines, defaults, context):
        if data_record.get('shipping_amount', False) and float(data_record.get('shipping_amount', False)) > 0:
            ctx = context.copy()
            ctx.update({
                'ext_tax_field': 'shipping_tax_amount',
            })
            res = self.add_order_extra_line(cr, uid, res, data_record, 'shipping_amount', 'SHIP MAGENTO', ctx)
        return res
    
    def add_order_shipping(self, cr, uid, res, external_referential_id, data_record, key_field, mapping_lines, defaults, context):
        if data_record.get('shipping_amount', False) and float(data_record.get('shipping_amount', False)) > 0:
            ctx = context.copy()
            ctx.update({
                'ext_tax_field': 'shipping_tax_amount',
            })
            res = self.add_order_extra_line(cr, uid, res, data_record, 'shipping_amount', 'SHIP MAGENTO', ctx)
        return res

    def add_gift_certificates(self, cr, uid, res, external_referential_id, data_record, key_field, mapping_lines, defaults, context):
        if data_record.get('giftcert_amount', False) and float(data_record.get('giftcert_amount', False)) > 0:
            ctx = context.copy()
            ctx.update({
                'ext_code_field': 'giftcert_code',
                'sign': -1,
            })
            res = self.add_order_extra_line(cr, uid, res, data_record, 'giftcert_amount', 'GIFT CERTIFICATE', ctx)
        return res

    def add_discount(self, cr, uid, res, external_referential_id, data_record, key_field, mapping_lines, defaults, context):
        if data_record.get('discount_amount', False) and float(data_record.get('discount_amount', False)) < 0:
            ctx = context.copy()
            ctx.update({
                'ext_code_field': 'coupon_code',
            })
            res = self.add_order_extra_line(cr, uid, res, data_record, 'discount_amount', 'DISCOUNT MAGENTO', ctx)
        return res

    def add_cash_on_delivery(self, cr, uid, res, external_referential_id, data_record, key_field, mapping_lines, defaults, context):
        if data_record.get('cod_fee', False) and float(data_record.get('cod_fee', False)) > 0:
            ctx = context.copy()
            ctx.update({
                'ext_tax_field': 'cod_tax_amount',
            })
            res = self.add_order_extra_line(cr, uid, res, data_record, 'cod_fee', 'CASH ON DELIVERY MAGENTO', ctx)
        return res   
     
    def oevals_from_extdata(self, cr, uid, external_referential_id, data_record, key_field, mapping_lines, defaults, context):
        if not context.get('one_by_one', False):
            if data_record.get('billing_address', False):
                defaults = self.get_order_addresses(cr, uid, defaults, external_referential_id, data_record, key_field, mapping_lines, defaults, context)
        
        res = super(magerp_osv.magerp_osv, self).oevals_from_extdata(cr, uid, external_referential_id, data_record, key_field, mapping_lines, defaults, context)

        if not context.get('one_by_one', False):
            if data_record.get('items', False):
                try:
                    res = self.get_order_lines(cr, uid, res, external_referential_id, data_record, key_field, mapping_lines, defaults, context)
                    res = self.add_order_shipping(cr, uid, res, external_referential_id, data_record, key_field, mapping_lines, defaults, context)
                    res = self.add_gift_certificates(cr, uid, res, external_referential_id, data_record, key_field, mapping_lines, defaults, context)
                    res = self.add_discount(cr, uid, res, external_referential_id, data_record, key_field, mapping_lines, defaults, context)
                    res = self.add_cash_on_delivery(cr, uid, res, external_referential_id, data_record, key_field, mapping_lines, defaults, context)
                except Exception, e:
                    print "order has errors with items lines, data are: ", data_record
                    print e
                    #TODO flag that the order has an error, especially.
            if data_record.get('status_history', False) and len(data_record['status_history']) > 0:
                res['date_order'] = data_record['status_history'][len(data_record['status_history'])-1]['created_at']
            if data_record.get('payment', False) and data_record['payment'].get('method', False):
                payment_settings = self.payment_code_to_payment_settings(cr, uid, data_record['payment']['method'], context)
                if payment_settings:
                    res['order_policy'] = payment_settings.order_policy
                    res['picking_policy'] = payment_settings.picking_policy
                    res['invoice_quantity'] = payment_settings.invoice_quantity
        return res

    def oe_create(self, cr, uid, vals, data, external_referential_id, defaults, context):
        order_id = super(magerp_osv.magerp_osv, self).oe_create(cr, uid, vals, data, external_referential_id, defaults, context)
        paid = self.create_payments(cr, uid, data, order_id, context)
        self.oe_status(cr, uid, order_id, paid, context)
        #TODO auto_reconcile invoice and statement depending on is_auto_reconcile param
        return order_id
    
    def create_payments(self, cr, uid, data_record, order_id, context):
        paid = False
        if data_record.get('payment', False):
            payment = data_record['payment']
            amount = False
            if payment.get('amount_paid', False):
                amount =  payment.get('amount_paid', False)
                paid = True
            elif payment.get('amount_ordered', False):
                amount =  payment.get('amount_ordered', False)
            if amount:
                order = self.pool.get('sale.order').browse(cr, uid, order_id, context)
                self.generate_payment_with_pay_code(cr, uid, payment['method'], order.partner_id.id, float(amount), "mag_" + payment['payment_id'], "mag_" + data_record['increment_id'], order.date_order, paid, context) 
        return paid

# UPDATE ORDER STATUS FROM MAGENTO TO OPENERP IS UNSTABLE, AND NOT VERY USEFULL. MAYBE IT WILL BE REFACTORED 

    #def oe_update(self,cr, uid, existing_rec_id, vals, data, external_referential_id, defaults, context):
        #order_line_ids = self.pool.get('sale.order.line').search(cr,uid,[('order_id','=', existing_rec_id)])
        #self.pool.get('sale.order.line').unlink(cr, uid, order_line_ids)
        #TODO update order status eventually (that would be easier if they were linked by some foreign key...)
        #self.oe_status(cr, uid, data, existing_rec_id, context)
        #return super(magerp_osv.magerp_osv, self).oe_update(cr, uid, existing_rec_id, vals, data, external_referential_id, defaults, context)

    #def oe_status(self, cr, uid, data, order_id, context):
        #wf_service = netsvc.LocalService("workflow")
        #if data.get('status_history', False) and len(data['status_history']) > 0 and data['status_history'][0]['status'] == 'canceled':
        #   wf_service.trg_validate(uid, 'sale.order', order_id, 'cancel', cr)
        #else:
        #   super(magerp_osv.magerp_osv, self).oe_status(cr, uid, order_id, context)
    
sale_order()
