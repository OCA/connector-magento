# -*- encoding: utf-8 -*-
#########################################################################
#                                                                       #
#########################################################################
#                                                                       #
# Copyright (C) 2011  Sharoon Thomas                                    #
# Copyright (C) 2009  Raphaël Valyi                                     #
# Copyright (C) 2011 Akretion Sébastien BEAU sebastien.beau@akretion.com#
# Copyright (C) 2011-2012 Camptocamp Guewen Baconnier                   #
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
import pooler
import magerp_osv
import netsvc
from tools.translate import _
import string
#from datetime import datetime
import tools
import time
from tools import DEFAULT_SERVER_DATETIME_FORMAT

DEBUG = True
NOTRY = False

#TODO, may be move that on out CSV mapping, but not sure we can easily
#see OpenERP sale/sale.py and Magento app/code/core/Mage/Sales/Model/Order.php for details
ORDER_STATUS_MAPPING = {'draft': 'processing', 'progress': 'processing', 'shipping_except': 'complete', 'invoice_except': 'complete', 'done': 'closed', 'cancel': 'canceled', 'waiting_date': 'holded'}
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

    def _get_default_storeview_id(self, cr, uid, ids, prop, unknow_none, context=None):
        res = {}
        for shop in self.browse(cr, uid, ids, context):
            if shop.default_storeview_integer_id:
                rid = self.pool.get('magerp.storeviews').extid_to_oeid(cr, uid, shop.default_storeview_integer_id, shop.referential_id.id)
                res[shop.id] = rid
            else:
                res[shop.id] = False
        return res
    
    def export_images(self, cr, uid, ids, context=None):
        if context is None: context = {}
        logger = netsvc.Logger()
        start_date = time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        image_obj = self.pool.get('product.images')
        for shop in self.browse(cr, uid, ids):
            context['shop_id'] = shop.id
            context['external_referential_id'] = shop.referential_id.id
            context['conn_obj'] = shop.referential_id.external_connection()
            context['last_images_export_date'] = shop.last_images_export_date
            exportable_product_ids = self.read(cr, uid, shop.id, ['exportable_product_ids'], context=context)['exportable_product_ids']
            res = self.pool.get('product.product').get_exportable_images(cr, uid, exportable_product_ids, context=context)
            if res:
                logger.notifyChannel('ext synchro', netsvc.LOG_INFO, "Creating %s images" %(len(res['to_create'])))
                logger.notifyChannel('ext synchro', netsvc.LOG_INFO, "Updating %s images" %(len(res['to_update'])))
                image_obj.update_remote_images(cr, uid, res['to_update']+res['to_create'], context)
            self.write(cr,uid,context['shop_id'],{'last_images_export_date': start_date})
        return True
               
  
    def _get_rootcategory(self, cr, uid, ids, prop, unknow_none, context=None):
        res = {}
        for shop in self.browse(cr, uid, ids, context):
            if shop.root_category_id and shop.shop_group_id.referential_id:
                rid = self.pool.get('product.category').extid_to_oeid(cr, uid, shop.root_category_id, shop.shop_group_id.referential_id.id)
                res[shop.id] = rid
            else:
                res[shop.id] = False
        return res

    def _set_rootcategory(self, cr, uid, id, name, value, fnct_inv_arg, context=None):
        ir_model_data_obj = self.pool.get('ir.model.data')
        shop = self.browse(cr, uid, id, context=context)
        if shop.root_category_id:
            model_data_id = self.pool.get('product.category').\
            extid_to_existing_oeid(cr, uid, shop.root_category_id, shop.referential_id.id, context=context)
            if model_data_id:
                ir_model_data_obj.write(cr, uid, model_data_id, {'res_id' : value}, context=context)
            else:
                raise osv.except_osv(_('Warning!'), _('No external id found, are you sure that the referential are syncronized? Please contact your administrator. (more information in magentoerpconnect/sale.py)'))
        return True

    def _get_exportable_root_category_ids(self, cr, uid, ids, prop, unknow_none, context=None):
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
        'allow_magento_order_status_push': fields.boolean('Allow Magento Order Status push', help='Allow to send back order status to Magento if order status changed in OpenERP first?'),
        'allow_magento_notification': fields.boolean('Allow Magento Notification', help='Allow Magento to notify customer (mail) if OpenERP update Magento order status?'),
    }   

    _defaults = {
        'allow_magento_order_status_push': lambda * a: False,
        'allow_magento_notification': lambda * a: False,
    }


    def import_shop_orders(self, cr, uid, shop, defaults, context=None):
        if context is None: context = {}
        result = super(sale_shop, self).import_shop_orders(cr, uid, shop, defaults=defaults, context=context)
        [result.setdefault(key, []) for key in ['create_ids', 'write_ids', 'unchanged_ids']]
        if shop.magento_shop:
            self.check_need_to_update(cr, uid, [shop.id], context=context)
            for storeview in shop.storeview_ids:
                magento_storeview_id = self.pool.get('magerp.storeviews').oeid_to_extid(cr, uid, storeview.id, shop.referential_id.id, context={})
                ids_or_filter = {'store_id': {'eq': magento_storeview_id}, 'state': {'neq': 'canceled'}}
                if shop.import_orders_from_date:
                    ids_or_filter.update({'created_at' : {'gt': shop.import_orders_from_date}})
                nb_last_created_ids = SALE_ORDER_IMPORT_STEP
                while nb_last_created_ids:
                    defaults['magento_storeview_id'] = storeview.id
                    ctx = context.copy()
                    ctx['ids_or_filter'] = ids_or_filter
                    resp = self.pool.get('sale.order').mage_import_base(cr, uid, context.get('conn_obj', False),
                                                                        shop.referential_id.id, defaults=defaults,
                                                                        context=ctx)
                    result['create_ids'] += resp.get('create_ids', [])
                    result['write_ids'] += resp.get('write_ids', [])
                    result['unchanged_ids'] += resp.get('unchanged_ids', [])
                    nb_last_created_ids = len(resp.get('create_ids', []) + resp.get('write_ids', []) + resp.get('unchanged_ids', []))
                    print nb_last_created_ids
        return result

    def check_need_to_update(self, cr, uid, ids, context=None):
        """ This function will update the order status in OpenERP for
        the order which are in the state 'need to update' """
        so_obj = self.pool.get('sale.order')

        for shop in self.browse(cr, uid, ids):
            conn = shop.referential_id.external_connection()
            # Update the state of orders in OERP that are in "need_to_update":True
            # from the Magento's corresponding orders
    
            # Get all need_to_update orders in OERP
            orders_to_update = so_obj.search(
                cr, uid,
                [('need_to_update', '=', True),
                 ('shop_id', '=', shop.id)],
                context=context)
            so_obj.check_need_to_update(
                cr, uid, orders_to_update, conn, context=context)
        return False

    def update_shop_orders(self, cr, uid, order, ext_id, context=None):
        if context is None: context = {}
        result = {}

        if order.shop_id.allow_magento_order_status_push:
            sale_obj = self.pool.get('sale.order')
            #status update:
            conn = context.get('conn_obj', False)
            status = ORDER_STATUS_MAPPING.get(order.state, False)
            if status:
                result['status_change'] = conn.call(
                    'sales_order.addComment',
                    [ext_id, status, '',
                     order.shop_id.allow_magento_notification])
                # If status has changed into OERP and the order need_to_update,
                # then we consider the update is done
                # remove the 'need_to_update': True
                if order.need_to_update:
                    sale_obj.write(
                        cr, uid, order.id, {'need_to_update': False})

            sale_obj.export_invoice(
                cr, uid, order, conn, ext_id, context=context)
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
        'is_magento': fields.related(
            'shop_id', 'referential_id', 'magento_referential',
            type='boolean',
            string='Is a Magento Sale Order')
    }
    
    def _auto_init(self, cr, context=None):
        tools.drop_view_if_exists(cr, 'sale_report')
        cr.execute("ALTER TABLE sale_order_line ALTER COLUMN discount TYPE numeric(16,6);")
        cr.execute("ALTER TABLE account_invoice_line ALTER COLUMN discount TYPE numeric(16,6);")
        self.pool.get('sale.report').init(cr)
        super(sale_order, self)._auto_init(cr, context)
        
    def get_mage_customer_address_id(self, address_data):
        if address_data.get('customer_address_id', False):
            return {'customer_address_id': address_data['customer_address_id'], 'is_magento_order_address': False}
        else:
            return {'customer_address_id': 'mag_order' + str(address_data['address_id']), 'is_magento_order_address': True}
    
    def get_order_addresses(self, cr, uid, res, external_referential_id, data_record, key_field, mapping_lines, defaults, context=None):
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
        if res is None:
            res = {}
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
        #TODO replace me by a generic function maybe the best solution will to have a field vat and a flag vat_ok and a flag force vat_ok
        #And so it's will be possible to have an invalid vat number (imported from magento for exemple) but the flag will be not set
        #Also we should think about the way to update customer. Indeed by default there are never updated
        if data_record.get('customer_taxvat'):
            partner_vals = {'mag_vat': data_record.get('customer_taxvat')}
            cr.execute('select * from ir_module_module where name=%s and state=%s', ('base_vat','installed'))
            if cr.fetchone(): 
                allchars = string.maketrans('', '')
                delchars = ''.join([c for c in allchars if c not in string.letters + string.digits])
                vat = data_record['customer_taxvat'].translate(allchars, delchars).upper()
                vat_country, vat_number = vat[:2].lower(), vat[2:]
                if 'check_vat_' + vat_country in dir(partner_obj):
                    check = getattr(partner_obj, 'check_vat_' + vat_country)
                    vat_ok = check(vat_number)
                else:
                    # Maybe magento vat number has not country code prefix. Take it from billing address.
                    if 'country_id' in data_record['billing_address']:
                        fnct = 'check_vat_' + data_record['billing_address']['country_id'].lower()
                        if fnct in dir(partner_obj):
                            check = getattr(partner_obj, fnct)
                            vat_ok = check(vat)
                            vat = data_record['billing_address']['country_id'] + vat
                        else:
                            vat_ok = False
                if vat_ok:
                    partner_vals.update({'vat_subjected':True, 'vat':vat})
            partner_obj.write(cr, uid, [partner_id], partner_vals)
        return res
    

    def add_order_extra_line(self, cr, uid, res, data_record, ext_field, product_ref, defaults, context=None):
        """ Add or substract amount on order as a separate line item with single quantity for each type of amounts like :
        shipping, cash on delivery, discount, gift certificates...

        @param res: dict of the order to create
        @param data_record: full data dict of the order
        @param ext_field: name of the field in data_record where the amount of the extra lineis stored
        @param product_ref: tuple with module and xml_id (module, xml_id) of the product to use for the extra line

        Optional arguments in context:
        sign: multiply the amount with the sign to add or substract it from the sale order
        ext_tax_field: name of the field in data_record where the tax amount is stored
        ext_code_field: name of the field in data_record containing a code (for coupons and gift certificates) which will be printed on the product name
        """
        if context is None: context = {}
        model_data_obj = self.pool.get('ir.model.data')
        sign = 'sign' in context and context['sign'] or 1
        ext_tax_field = 'ext_tax_field' in context and context['ext_tax_field'] or None
        ext_code_field = 'ext_code_field' in context and context['ext_code_field'] or None

        model, product_id = model_data_obj.get_object_reference(cr, uid, *product_ref)
        product = self.pool.get('product.product').browse(cr, uid, product_id, context)
        is_tax_included = context.get('price_is_tax_included', False)
        amount = float(data_record[ext_field]) * sign
        name = product.name
        if ext_code_field and data_record.get(ext_code_field, False):
            name = "%s [%s]" % (name, data_record[ext_code_field])
		
        if is_tax_included:
            price_unit = float(amount) + float(data_record[ext_tax_field])
        else:
            price_unit = float(amount)

        extra_line = {
                        'product_id': product.id,
                        'name': name,
                        'product_uom': product.uom_id.id,
                        'product_uom_qty': 1,
                        'price_unit': price_unit,
                    }

        if not res.get('order_line'):
            res['order_line'] = []

        if context.get('play_sale_order_onchange'):
            extra_line = self.pool.get('sale.order.line').play_sale_order_line_onchange(cr, uid, extra_line, res, res['order_line'], defaults, context=context)
        if context.get('use_external_tax'):
            tax_vat = abs(float(data_record[ext_tax_field]) / amount)
            line_tax_id = self.pool.get('account.tax').get_tax_from_rate(cr, uid, tax_vat, context.get('is_tax_included'), context=context)
            extra_line['tax_id'] = [(6, 0, line_tax_id)]
        res['order_line'].append((0, 0, extra_line))

        return res
    
    def add_order_shipping(self, cr, uid, res, external_referential_id, data_record, defaults, context=None):
        if context is None: context = {}
        if data_record.get('shipping_amount', False) and float(data_record.get('shipping_amount', False)) > 0:
            ctx = context.copy()
            ctx.update({
                'ext_tax_field': 'shipping_tax_amount',
            })
            product_ref = ('base_sale_multichannels', 'product_product_shipping')
            res = self.add_order_extra_line(cr, uid, res, data_record, 'shipping_amount', product_ref, defaults, ctx)
        return res

    def add_gift_certificates(self, cr, uid, res, external_referential_id, data_record, defaults, context=None):
        if context is None: context = {}
        if data_record.get('giftcert_amount', False) and float(data_record.get('giftcert_amount', False)) > 0:
            ctx = context.copy()
            ctx.update({
                'ext_code_field': 'giftcert_code',
                'sign': -1,
            })
            product_ref = ('magentoerpconnect', 'product_product_gift')
            res = self.add_order_extra_line(cr, uid, res, data_record, 'giftcert_amount', product_ref, defaults, ctx)
        return res

    def add_discount(self, cr, uid, res, external_referential_id, data_record, defaults, context=None):
        #TODO fix me rev 476
        #if data_record.get('discount_amount', False) and float(data_record.get('discount_amount', False)) < 0:
        #    ctx = context.copy()
        #    ctx.update({
        #        'ext_code_field': 'coupon_code',
        #    })
        #    product_ref = ('magentoerpconnect', 'product_product_discount')
        #    res = self.add_order_extra_line(cr, uid, res, data_record, 'discount_amount', product_ref, defaults, ctx)
        return res

    def add_cash_on_delivery(self, cr, uid, res, external_referential_id, data_record, defaults, context=None):
        if context is None: context = {}
        if data_record.get('cod_fee', False) and float(data_record.get('cod_fee', False)) > 0:
            ctx = context.copy()
            ctx.update({
                'ext_tax_field': 'cod_tax_amount',
            })
            product_ref = ('magentoerpconnect', 'product_product_cash_on_delivery')
            res = self.add_order_extra_line(cr, uid, res, data_record, 'cod_fee', product_ref, defaults, ctx)
        return res
    
    def convert_extdata_into_oedata(self, cr, uid, external_data, external_referential_id, parent_data=None, defaults=None, context=None):
        res = super(sale_order, self).convert_extdata_into_oedata(cr, uid, external_data, external_referential_id, parent_data=parent_data, defaults=defaults, context=context)
        res=res[0]
        external_data = external_data[0]
        res = self.add_order_shipping(cr, uid, res, external_referential_id, external_data, defaults, context)
        res = self.add_gift_certificates(cr, uid, res, external_referential_id, external_data, defaults, context)
        res = self.add_discount(cr, uid, res, external_referential_id, external_data, defaults, context)
        res = self.add_cash_on_delivery(cr, uid, res, external_referential_id, external_data, defaults, context)
        return [res]

    def _merge_sub_items(self, cr, uid, product_type, top_item, child_items, context=None):
        """
        Manage the sub items of the magento sale order lines. A top item contains one
        or many child_items. For some product types, we want to merge them in the main
        item, or keep them as order line.

        A list may be returned to add many items (ie to keep all child_items as items.

        :param top_item: main item (bundle, configurable)
        :param child_items: list of childs of the top item
        :return: item or list of items
        """
        if product_type == 'configurable':
            item = top_item.copy()
            # For configurable product all information regarding the price is in the configurable item
            # In the child a lot of information is empty, but contains the right sku and product_id
            # So the real product_id and the sku and the name have to be extracted from the child
            for field in ['sku', 'product_id', 'name']:
                item[field] = child_items[0][field]
            return item
        return top_item

    def data_record_filter(self, cr, uid, data_record, context=None):
        child_items = {}  # key is the parent item id
        top_items = []

        # Group the childs with their parent
        for item in data_record['items']:
            if item.get('parent_item_id'):
                child_items.setdefault(item['parent_item_id'], []).append(item)
            else:
                top_items.append(item)

        all_items = []
        for top_item in top_items:
            if top_item['item_id'] in child_items:
                item_modified = self._merge_sub_items(cr, uid,
                                                      top_item['product_type'],
                                                      top_item,
                                                      child_items[top_item['item_id']],
                                                      context=context)
                if not isinstance(item_modified, list):
                    item_modified = [item_modified]
                all_items.extend(item_modified)
            else:
                all_items.append(top_item)
        
        data_record['items'] = all_items
        return data_record

    def oevals_from_extdata(self, cr, uid, external_referential_id, data_record, key_field, mapping_lines, parent_data=None, previous_lines=None, defaults=None, context=None):
        if context is None: context = {}
        if data_record.get('items', False):
            data_record = self.data_record_filter(cr, uid, data_record, context=context)
        #TODO refactor this code regarding the new feature of sub-mapping in base_external_referential
        if not context.get('one_by_one', False):
            if data_record.get('billing_address', False):
                defaults = self.get_order_addresses(cr, uid, defaults, external_referential_id, data_record, key_field, mapping_lines, defaults, context)
        res = super(magerp_osv.magerp_osv, self).oevals_from_extdata(cr, uid, external_referential_id, data_record, key_field, mapping_lines, parent_data, previous_lines, defaults, context)

        #Move me in a mapping
        if not context.get('one_by_one', False):            
            if data_record.get('status_history', False) and len(data_record['status_history']) > 0:
                res['date_order'] = data_record['status_history'][len(data_record['status_history'])-1]['created_at']
        return res

    def _parse_external_payment(self, cr, uid, order_data, context=None):
        """
        Parse the external order data and return if the sale order
        has been paid and the amount to pay or to be paid

        :param dict order_data: payment information of the magento sale
            order
        :return: tuple where :
            - first item indicates if the payment has been done (True or False)
            - second item represents the amount paid or to be paid
        """
        paid = amount = False
        payment_info = order_data.get('payment')
        if payment_info:
            amount = False
            if payment_info.get('amount_paid', False):
                amount =  payment_info.get('amount_paid', False)
                paid = True
            elif payment_info.get('amount_ordered', False):
                amount = payment_info.get('amount_ordered', False)
        return paid, amount

    def create_payments(self, cr, uid, order_id, data_record, context=None):
        if context is None:
            context = {}

        if 'Magento' in context.get('external_referential_type', ''):
            payment_info = data_record.get('payment')
            paid, amount = self._parse_external_payment(
                cr, uid, data_record, context=context)
            if amount:
                order = self.pool.get('sale.order').browse(
                    cr, uid, order_id, context)
                self.generate_payment_with_pay_code(
                    cr, uid,
                    payment_info['method'],
                    order.partner_id.id,
                    float(amount),
                    "mag_" + payment_info['payment_id'],
                    "mag_" + data_record['increment_id'],
                    order.date_order,
                    paid,
                    context=context)
        else:
            paid = super(sale_order, self).create_payments(
                cr, uid, order_id, data_record, context=context)
        return paid

    def _chain_cancel_orders(self, cr, uid, external_id, external_referential_id, defaults=None, context=None):
        """ Get all the chain of edited orders (an edited order is canceled on Magento)
         and cancel them on OpenERP. If an order cannot be canceled (confirmed for example)
         A request is created to inform the user.
        """
        if context is None:
            context = {}
        logger = netsvc.Logger()
        conn = context.get('conn_obj', False)
        parent_list = []
        # get all parents orders (to cancel) of the sale orders
        parent = conn.call('sales_order.get_parent', [external_id])
        while parent:
            parent_list.append(parent)
            parent = conn.call('sales_order.get_parent', [parent])

        wf_service = netsvc.LocalService("workflow")
        for parent_incr_id in parent_list:
            canceled_order_id = self.extid_to_existing_oeid(cr, uid, parent_incr_id, external_referential_id)
            if canceled_order_id:
                try:
                    wf_service.trg_validate(uid, 'sale.order', canceled_order_id, 'cancel', cr)
                    self.log(cr, uid, canceled_order_id, "order %s canceled when updated from external system" % (canceled_order_id,))
                    logger.notifyChannel('ext synchro', netsvc.LOG_INFO, "Order %s canceled when updated from external system because it has been replaced by a new one" % (canceled_order_id,))
                except osv.except_osv, e:
                    #TODO: generic reporting of errors in magentoerpconnect
                    # except if the sale order has been confirmed for example, we cannot cancel the order
                    to_cancel_order_name = self.read(cr, uid, canceled_order_id, ['name'])['name']
                    request = self.pool.get('res.request')
                    summary = _(("The sale order %s has been replaced by the sale order %s on Magento.\n"
                                 "The sale order %s has to be canceled on OpenERP but it is currently impossible.\n\n"
                                 "Error:\n"
                                 "%s\n"
                                 "%s")) % (parent_incr_id,
                                          external_id,
                                          to_cancel_order_name,
                                          e.name,
                                          e.value)
                    request.create(cr, uid,
                                   {'name': _("Could not cancel sale order %s during Magento's sale orders import") % (to_cancel_order_name,),
                                    'act_from': uid,
                                    'act_to': uid,
                                    'body': summary,
                                    'priority': '2'
                                    })

    def ext_import(self, cr, uid, data, external_referential_id, defaults=None, context=None):
        """
        Inherit the method to flag the order to "Imported" on Magento right after the importation
        Before the import, check if the order is already imported and in a such case, skip the import
         and flag "imported" on Magento.
        """

        #This check should be done by a decorator

        if context is None: context = {}
        if not (context.get('external_referential_type', False) and 'Magento' in context['external_referential_type']):
            return super(sale_order, self).ext_import(cr, uid, data, external_referential_id, defaults=defaults, context=context)

        res = {'create_ids': [], 'write_ids': []}
        ext_order_id = data[0]['increment_id']
        #the new cursor should be replaced by a beautiful decorator on ext_import
        order_cr = pooler.get_db(cr.dbname).cursor()
        try:
            if not self.extid_to_existing_oeid(order_cr, uid, ext_order_id, external_referential_id, context):
                res = super(sale_order, self).ext_import(order_cr, uid, data, external_referential_id, defaults=defaults, context=context)

                # if a created order has a relation_parent_real_id, the new one replaces the original, so we have to cancel the old one
                if data[0].get('relation_parent_real_id', False): # data[0] because orders are imported one by one so data always has 1 element
                    self._chain_cancel_orders(order_cr, uid, ext_order_id, external_referential_id, defaults=defaults, context=context)

            # set the "imported" flag to true on Magento
            self.ext_set_order_imported(order_cr, uid, ext_order_id, external_referential_id, context)
            order_cr.commit()
        finally:
            order_cr.close()
        return res

    def ext_set_order_imported(self, cr, uid, external_id, external_referential_id, context=None):
        if context is None:
            context = {}
        logger = netsvc.Logger()
        conn = context.get('conn_obj', False)
        conn.call('sales_order.done', [external_id])
        logger.notifyChannel('ext synchro', netsvc.LOG_INFO, "Successfully set the imported flag on Magento on sale order %s" % external_id)
        return True

    def mage_import_base(self, cr, uid, conn, external_referential_id, defaults=None, context=None):
        """ Inherited method for Sales orders in order to import only order not flagged as "imported" on Magento
        """
        logger = netsvc.Logger()
        if context is None:
            context = {}
        if not 'ids_or_filter' in context.keys():
            context['ids_or_filter'] = []
        result = {'create_ids': [], 'write_ids': []}

        mapping_id = self.pool.get('external.mapping').search(cr,uid,[('model', '=', self._name),
                                                                      ('referential_id', '=', external_referential_id)])
        if mapping_id:
            # returns the non already imported order (limit returns the n first orders)
            order_retrieve_params = {
                'imported': False,
                'limit': SALE_ORDER_IMPORT_STEP,
                'filters': context['ids_or_filter'],
            }
            ext_order_ids = conn.call('sales_order.search', [order_retrieve_params])
            order_ids_filtred=[]
            unchanged_ids=[]
            for ext_order_id in ext_order_ids:
                existing_id = self.extid_to_existing_oeid(cr, uid, ext_order_id, external_referential_id, context=context)
                if existing_id:
                    unchanged_ids.append(existing_id)
                    logger.notifyChannel('ext synchro', netsvc.LOG_INFO, "the order %s already exist in OpenERP" % (ext_order_id,))
                    self.ext_set_order_imported(cr, uid, ext_order_id, external_referential_id, context=context)
                else:
                    order_ids_filtred.append({'increment_id' : ext_order_id})
            context['conn_obj'] = conn # we will need the connection to set the flag to "imported" on magento after each order import
            result = self.mage_import_one_by_one(cr, uid, conn, external_referential_id, mapping_id[0], order_ids_filtred, defaults, context)
            result['unchanged_ids'] = unchanged_ids
        return result

    def _check_need_to_update_single(self, cr, uid, order, conn, context=None):
        """
        For one order, check on Magento if it has been paid since last
        check. If so, it will launch the defined flow based on the
        payment type (validate order, invoice, ...)

        :param browse_record order: browseable sale.order
        :param Connection conn: connection with Magento
        :return: True
        """
        model_data_obj = self.pool.get('ir.model.data')
        # check if the status has changed in Magento
        # We don't use oeid_to_extid function cause it only handles integer ids
        # Magento can have something like '100000077-2'
        model_data_ids = model_data_obj.search(
            cr, uid,
            [('model', '=', self._name),
             ('res_id', '=', order.id),
             ('external_referential_id', '=', order.shop_id.referential_id.id)],
            context=context)

        if model_data_ids:
            prefixed_id = model_data_obj.read(
                cr, uid, model_data_ids[0], ['name'], context=context)['name']
            ext_id = self.id_from_prefixed_id(prefixed_id)
        else:
            return False

        data_record = conn.call('sales_order.info', [ext_id])

        if data_record['status'] == 'canceled':
            wf_service = netsvc.LocalService("workflow")
            wf_service.trg_validate(uid, 'sale.order', order.id, 'cancel', cr)
            updated = True
            self.log(cr, uid, order.id, "order %s canceled when updated from external system" % (order.id,))
        # If the order isn't canceled and was waiting for a payment,
        # so we follow the standard flow according to ext_payment_method:
        else:
            paid, __ = self._parse_external_payment(
                cr, uid, data_record, context=context)
            self.oe_status(cr, uid, order.id, paid, context)
            # create_payments has to be done after oe_status
            # because oe_status creates the invoice
            # and create_payment could reconcile the payment
            # with the invoice

            updated = self.create_payments(
                cr, uid, order.id, data_record, context)
            if updated:
                self.log(
                    cr, uid, order.id,
                    "order %s paid when updated from external system" %
                    (order.id,))
        # Untick the need_to_update if updated (if so was canceled in magento
        # or if it has been paid through magento)
        if updated:
            self.write(cr, uid, order.id, {'need_to_update': False})
        cr.commit()
        return True

    def check_need_to_update(self, cr, uid, ids, conn, context=None):
        """
        For each order, check on Magento if it has been paid since last
        check. If so, it will launch the defined flow based on the
        payment type (validate order, invoice, ...)

        :param Connection conn: connection with Magento
        :return: True
        """
        for order in self.browse(cr, uid, ids, context=context):
            self._check_need_to_update_single(
                cr, uid, order, conn, context=context)
        return True

    def _create_external_invoice(self, cr, uid, order, conn, ext_id,
                                context=None):
        """ Creation of an invoice on Magento."""
        magento_invoice_ref = conn.call(
            'sales_order_invoice.create',
            [order.magento_incrementid,
            [],
             _("Invoice Created"),
             True,
             order.shop_id.allow_magento_notification])
        return magento_invoice_ref

    # TODO Move in base_sale_multichannels?
    def export_invoice(self, cr, uid, order, conn, ext_id, context=None):
        """ Export an invoice on external referential """
        cr.execute("select account_invoice.id "
                   "from account_invoice "
                   "inner join sale_order_invoice_rel "
                   "on invoice_id = account_invoice.id "
                   "where order_id = %s" % order.id)
        resultset = cr.fetchone()
        created = False
        if resultset and len(resultset) == 1:
            invoice = self.pool.get("account.invoice").browse(
                cr, uid, resultset[0], context=context)
            if (invoice.amount_total == order.amount_total and
                not invoice.magento_ref):
                try:
                    self._create_external_invoice(
                        cr, uid, order, conn, ext_id, context=context)
                    created = True
                except Exception, e:
                    self.log(cr, uid, order.id,
                             "failed to create Magento invoice for order %s" %
                             (order.id,))
                    # TODO make sure that's because Magento invoice already
                    # exists and then re-attach it!
        return created

sale_order()

