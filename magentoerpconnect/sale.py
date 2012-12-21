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

from openerp.osv.orm import Model
from openerp.osv import fields
from openerp.osv.osv import except_osv
import netsvc
from tools.translate import _
from openerp import tools
import time
from tools import DEFAULT_SERVER_DATETIME_FORMAT
from base_external_referentials.external_osv import ExternalSession
from base_external_referentials.decorator import only_for_referential, open_report

#from base_external_referentials import report

import logging
_logger = logging.getLogger(__name__)

DEBUG = True
NOTRY = False

#TODO, may be move that on out CSV mapping, but not sure we can easily
#see OpenERP sale/sale.py and Magento app/code/core/Mage/Sales/Model/Order.php for details
ORDER_STATUS_MAPPING = {
    'manual': 'processing',
    'progress': 'processing',
    'shipping_except': 'complete',
    'invoice_except': 'complete',
    'done': 'complete',
    'cancel': 'canceled',
    'waiting_date': 'holded'}
SALE_ORDER_IMPORT_STEP = 200

class sale_shop(Model):
    _inherit = "sale.shop"

    @only_for_referential('magento')
    def init_context_before_exporting_resource(self, cr, uid, external_session, object_id, resource_name, context=None):
        context = super(sale_shop, self).init_context_before_exporting_resource(cr, uid, external_session, object_id, resource_name, context=context)
        shop = self.browse(cr, uid, object_id, context=context)
        context['main_lang'] = shop.referential_id.default_lang_id.code
        context['lang_to_export'] = [shop.referential_id.default_lang_id.code]
        context['storeview_to_lang'] = {}
        for storeview in shop.storeview_ids:
            if storeview.lang_id and storeview.lang_id.code != shop.referential_id.default_lang_id.code:
                context['storeview_to_lang'][storeview.code] = storeview.lang_id.code
                if not storeview.lang_id.code in context['lang_to_export']:
                    context['lang_to_export'].append(storeview.lang_id.code)
        return context

    def _get_exportable_product_ids(self, cr, uid, ids, name, args, context=None):
        res = super(sale_shop, self)._get_exportable_product_ids(cr, uid, ids, name, args, context=None)
        for shop_id in res:
            website_id =  self.read(cr, uid, shop_id, ['shop_group_id'])
            if website_id.get('shop_group_id', False):
                res[shop_id] = self.pool.get('product.product').search(cr, uid,
                                                                       [('magento_exportable', '=', True),
                                                                        ('id', 'in', res[shop_id]),
                                                                        "|", ('websites_ids', 'in', [website_id['shop_group_id'][0]]),
                                                                             ('websites_ids', '=', False)])
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
        start_date = time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        image_obj = self.pool.get('product.images')
        for shop in self.browse(cr, uid, ids):
            external_session = ExternalSession(shop.referential_id, shop)
            exportable_product_ids = self.read(cr, uid, shop.id, ['exportable_product_ids'], context=context)['exportable_product_ids']
            res = self.pool.get('product.product').get_exportable_images(cr, uid, external_session, exportable_product_ids, context=context)
            if res:
                _logger.info("Creating %s images", len(res['to_create']))
                _logger.info("Updating %s images", len(res['to_update']))
                image_obj.update_remote_images(cr, uid, external_session, res['to_update']+res['to_create'], context)
            self.pool.get('product.images')._set_last_exported_date(cr, uid, external_session, start_date, context=context)
        return True

    #TODO refactor the ay to export images
    #No time for doing it now so I just overwrite the generic function
    #In order to use the actual implementation

    def export_resources(self, cr, uid, ids, resource_name, context=None):
        if resource_name == 'product.images':
            return self.export_images(cr, uid, ids, context=context)
        else:
            return super(sale_shop, self).export_resources(cr, uid, ids, resource_name, context=context)

    def _get_rootcategory(self, cr, uid, ids, name, value, context=None):
        res = {}
        for shop in self.browse(cr, uid, ids, context):
            if shop.root_category_id and shop.shop_group_id.referential_id:
                rid = self.pool.get('product.category').extid_to_existing_oeid(
                    cr, uid, shop.shop_group_id.referential_id.id, shop.root_category_id)
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
                raise except_osv(_('Warning!'),
                                 _('No external id found, are you sure that the referential are syncronized? '
                                   'Please contact your administrator. '
                                   '(more information in magentoerpconnect/sale.py)'))
        return True

    def _get_exportable_root_category_ids(self, cr, uid, ids, prop, unknow_none, context=None):
        res = {}
        res1 = self._get_rootcategory(cr, uid, ids, prop, unknow_none, context)
        for shop in self.browse(cr, uid, ids, context):
            res[shop.id] = res1[shop.id] and [res1[shop.id]] or []
        return res

    @only_for_referential('magento')
    def _get_default_import_values(self, cr, uid, external_session, **kwargs):
        defaults = super(sale_shop, self)._get_default_import_values(cr, uid, external_session, **kwargs)
        if not defaults: defaults={}
        defaults.update({'magento_shop' : True})
        return defaults

    @only_for_referential('magento')
    @open_report
    def _export_inventory(self, *args, **kwargs):
        return super(sale_shop, self)._export_inventory(*args, **kwargs)

    _columns = {
        'default_storeview_integer_id':fields.integer('Magento default Storeview ID'), #This field can't be a many2one because store field will be mapped before creating storeviews
        'default_storeview_id':fields.function(_get_default_storeview_id, type="many2one", relation="magerp.storeviews", method=True, string="Default Storeview"),
        'root_category_id':fields.integer('Root product Category'), #This field can't be a many2one because store field will be mapped before creating category
        'magento_root_category':fields.function(_get_rootcategory, fnct_inv = _set_rootcategory, type="many2one", relation="product.category", string="Root Category"),
        'exportable_root_category_ids': fields.function(_get_exportable_root_category_ids, type="many2many", relation="product.category", method=True, string="Root Category"), #fields.function(_get_exportable_root_category_ids, type="many2one", relation="product.category", method=True, 'Exportable Root Categories'),
        'storeview_ids': fields.one2many('magerp.storeviews', 'shop_id', 'Store Views'),
        'exportable_product_ids': fields.function(_get_exportable_product_ids, method=True, type='one2many', relation="product.product", string='Exportable Products'),
        #TODO fix me, it's look like related field on a function fielf doesn't work.
        #'magento_shop': fields.related('referential_id', 'magento_referential',type="boolean", string='Magento Shop', readonly=True),
        'magento_shop': fields.boolean('Magento Shop', readonly=True),
        'allow_magento_order_status_push': fields.boolean('Allow Magento Order Status push', help='Allow to send back order status to Magento if order status changed in OpenERP first?'),
        'allow_magento_notification': fields.boolean('Allow Magento Notification', help='Allow Magento to notify customer with an e-mail when OpenERP change an order status, create an invoice or a delivery order on Magento.'),
    }

    _defaults = {
        'allow_magento_order_status_push': lambda * a: False,
        'allow_magento_notification': lambda * a: False,
    }

    def _get_magento_status(self, cr, uid, order, context=None):
        return ORDER_STATUS_MAPPING.get(order.state)

    def update_shop_orders(self, cr, uid, external_session, order, ext_id, context=None):
        if context is None: context = {}
        result = False
        if order.shop_id.allow_magento_order_status_push:
            sale_obj = self.pool.get('sale.order')
            #status update:
            status = self._get_magento_status(cr, uid, order, context=context)
            if status:
                result = external_session.connection.call(
                    'sales_order.addComment',
                    [ext_id, status, '',
                     order.shop_id.allow_magento_notification])
                #TODO REMOVE ME
                # If status has changed into OERP and the order need_to_update,
                # then we consider the update is done
                # remove the 'need_to_update': True
                if order.need_to_update:
                    sale_obj.write(
                        cr, uid, order.id, {'need_to_update': False})
        return result

    def _sale_shop(self, cr, uid, callback, context=None):
        if context is None:
            context = {}
        proxy = self.pool.get('sale.shop')
        domain = [ ('magento_shop', '=', True), ('auto_import', '=', True) ]

        ids = proxy.search(cr, uid, domain, context=context)
        if ids:
            callback(cr, uid, ids, context=context)

        # tools.debug(callback)
        # tools.debug(ids)
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

    def run_import_check_need_to_update(self, cr, uid, context=None):
        self._sale_shop(cr, uid, self.check_need_to_update, context=context)


class sale_order(Model):
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

#TODO reimplement the check on tva in a good way
#        # Adds vat number (country code+magento vat) if base_vat module is installed and Magento sends customer_taxvat
#        #TODO replace me by a generic function maybe the best solution will to have a field vat and a flag vat_ok and a flag force vat_ok
#        #And so it's will be possible to have an invalid vat number (imported from magento for exemple) but the flag will be not set
#        #Also we should think about the way to update customer. Indeed by default there are never updated
#        if data_record.get('customer_taxvat'):
#            partner_vals = {'mag_vat': data_record.get('customer_taxvat')}
#            cr.execute('select * from ir_module_module where name=%s and state=%s', ('base_vat','installed'))
#            if cr.fetchone():
#                allchars = string.maketrans('', '')
#                delchars = ''.join([c for c in allchars if c not in string.letters + string.digits])
#                vat = data_record['customer_taxvat'].translate(allchars, delchars).upper()
#                vat_country, vat_number = vat[:2].lower(), vat[2:]
#                if 'check_vat_' + vat_country in dir(partner_obj):
#                    check = getattr(partner_obj, 'check_vat_' + vat_country)
#                    vat_ok = check(vat_number)
#                else:
#                    # Maybe magento vat number has not country code prefix. Take it from billing address.
#                    if 'country_id' in data_record['billing_address']:
#                        fnct = 'check_vat_' + data_record['billing_address']['country_id'].lower()
#                        if fnct in dir(partner_obj):
#                            check = getattr(partner_obj, fnct)
#                            vat_ok = check(vat)
#                            vat = data_record['billing_address']['country_id'] + vat
#                        else:
#                            vat_ok = False
#                if vat_ok:
#                    partner_vals.update({'vat_subjected':True, 'vat':vat})
#            partner_obj.write(cr, uid, [partner_id], partner_vals)
#        return res
#


    def _get_payment_information(self, cr, uid, external_session, order_id, resource, context=None):
        """
        Parse the external resource and return a dict of data converted
        """
        vals = super(sale_order, self)._get_payment_information(cr, uid, external_session, order_id, resource, context=context)
        payment_info = resource.get('payment')
        if payment_info and payment_info.get('amount_paid'):
            vals['paid'] = True
            vals['amount'] = float(payment_info['amount_paid'])
        return vals

    def _chain_cancel_orders(self, cr, uid, external_id, external_referential_id, defaults=None, context=None):
        """ Get all the chain of edited orders (an edited order is canceled on Magento)
         and cancel them on OpenERP. If an order cannot be canceled (confirmed for example)
         A request is created to inform the user.
        """
        if context is None:
            context = {}
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
                    _logger.info("Order %s canceled when updated from external system because it has been replaced by a new one", canceled_order_id)
                except except_osv, e:
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

#NEW FEATURE

#TODO reimplement chain cancel orders
#                # if a created order has a relation_parent_real_id, the new one replaces the original, so we have to cancel the old one
#                if data[0].get('relation_parent_real_id', False): # data[0] because orders are imported one by one so data always has 1 element
#                    self._chain_cancel_orders(order_cr, uid, ext_order_id, external_referential_id, defaults=defaults, context=context)

    def _get_filter(self, cr, uid, external_session, step, previous_filter=None, context=None):
        magento_storeview_ids=[]
        shop = external_session.sync_from_object
        for storeview in shop.storeview_ids:
            magento_storeview_id = self.pool.get('magerp.storeviews').get_extid(cr, uid, storeview.id, shop.referential_id.id, context={})
            if magento_storeview_id:
                magento_storeview_ids.append(magento_storeview_id)

        mag_filter = {
            'state': {'neq': 'canceled'},
            'store_id': {'in': magento_storeview_ids},
            }

        if shop.import_orders_from_date:
            mag_filter.update({'created_at' : {'gt': shop.import_orders_from_date}})
        return {
            'imported': False,
            'limit': step,
            'filters': mag_filter,
        }

    def create_onfly_partner(self, cr, uid, external_session, resource, mapping, defaults, context=None):
        """
        As magento allow guest order we have to create an on fly partner without any external id
        """
        if not defaults: defaults={}
        local_defaults = defaults.copy()

        resource['firstname'] = resource['customer_firstname']
        resource['lastname'] = resource['customer_lastname']
        resource['email'] = resource['customer_email']

        shop = external_session.sync_from_object
        partner_defaults = {'website_id': shop.shop_group_id.id}
        res = self.pool.get('res.partner')._record_one_external_resource(cr, uid, external_session, resource,\
                                mapping=mapping, defaults=partner_defaults, context=context)
        partner_id = res.get('create_id') or res.get('write_id')

        local_defaults['partner_id'] = partner_id
        for address_key in ['partner_invoice_id', 'partner_shipping_id']:
            if not defaults.get(address_key): local_defaults[address_key] = {}
            local_defaults[address_key]['partner_id'] = partner_id
        return local_defaults

    @only_for_referential('magento')
    def _transform_one_resource(self, cr, uid, external_session, convertion_type, resource, mapping, mapping_id, \
                     mapping_line_filter_ids=None, parent_data=None, previous_result=None, defaults=None, context=None):
        resource = self.clean_magento_resource(cr, uid, resource, context=context)
        resource = self.clean_magento_items(cr, uid, resource, context=context)
        for line in mapping[mapping_id]['mapping_lines']:
            if line['name'] == 'customer_id' and not resource.get('customer_id'):
                #If there is not partner it's a guest order
                #So we remove the useless information
                #And create a partner on fly and set the data in the default value
                #We only do this if the customer_id is in the mapping line
                #Indeed when we check if a sale order exist only the name is asked for convertion
                resource.pop('customer_id', None)
                resource['billing_address'].pop('customer_id', None)
                resource['shipping_address'].pop('customer_id', None)
                defaults = self.create_onfly_partner(cr, uid, external_session, resource, mapping, defaults, context=context)

        return super(sale_order, self)._transform_one_resource(cr, uid, external_session, convertion_type, resource,\
                 mapping, mapping_id,  mapping_line_filter_ids=mapping_line_filter_ids, parent_data=parent_data,\
                 previous_result=previous_result, defaults=defaults, context=context)

    @only_for_referential('magento')
    def _get_external_resource_ids(self, cr, uid, external_session, resource_filter=None, mapping=None, mapping_id=None, context=None):
        res = super(sale_order, self)._get_external_resource_ids(cr, uid, external_session, resource_filter=resource_filter, mapping=mapping, mapping_id=mapping_id, context=context)
        order_ids_to_import=[]
        for external_id in res:
            existing_id = self.get_oeid(cr, uid, external_id, external_session.referential_id.id, context=context)
            if existing_id:
                external_session.logger.info(_("the order %s already exist in OpenERP") % (external_id,))
                self.ext_set_resource_as_imported(cr, uid, external_session, external_id, mapping=mapping, mapping_id=mapping_id, context=context)
            else:
                order_ids_to_import.append(external_id)
        return order_ids_to_import

    @only_for_referential('magento')
    def _record_one_external_resource(self, cr, uid, external_session, resource, defaults=None, mapping=None, mapping_id=None, context=None):
        res = super(sale_order, self)._record_one_external_resource(cr, uid, external_session, resource, defaults=defaults, mapping=mapping, mapping_id=mapping_id, context=context)
        external_id = resource['increment_id'] # TODO it will be better to not hardcode this parameter
        self.ext_set_resource_as_imported(cr, uid, external_session, external_id, mapping=mapping, mapping_id=mapping_id, context=context)
        return res

    @only_for_referential('magento')
    def _check_need_to_update_single(self, cr, uid, external_session, order, context=None):
        """
        For one order, check on Magento if it has been paid since last
        check. If so, it will launch the defined flow based on the
        payment type (validate order, invoice, ...)

        :param browse_record order: browseable sale.order
        :param Connection conn: connection with Magento
        :return: True
        """

        #TODO improve me and replace me by a generic function in base_sale_multichannels
        #Only the call to magento should be here

        model_data_obj = self.pool.get('ir.model.data')
        # check if the status has changed in Magento
        # We don't use oeid_to_extid function cause it only handles integer ids
        # Magento can have something like '100000077-2'
        model_data_ids = model_data_obj.search(
            cr, uid,
            [('model', '=', self._name),
             ('res_id', '=', order.id),
             ('referential_id', '=', order.shop_id.referential_id.id)],
            context=context)

        if model_data_ids:
            prefixed_id = model_data_obj.read(
                cr, uid, model_data_ids[0], ['name'], context=context)['name']
            ext_id = self.id_from_prefixed_id(prefixed_id)
        else:
            return False

        resource = external_session.connection.call('sales_order.info', [ext_id])

        if resource['status'] == 'canceled':
            wf_service = netsvc.LocalService("workflow")
            wf_service.trg_validate(uid, 'sale.order', order.id, 'cancel', cr)
            updated = True
            self.log(cr, uid, order.id, "order %s canceled when updated from external system" % (order.id,))
        # If the order isn't canceled and was waiting for a payment,
        # so we follow the standard flow according to ext_payment_method:
        else:
            updated = self.paid_and_update(cr, uid, external_session, order.id, resource, context=context)
            if updated:
                self.log(
                    cr, uid, order.id,
                    "order %s paid when updated from external system" %
                    (order.id,))
        # Untick the need_to_update if updated (if so was canceled in magento
        # or if it has been paid through magento)
        if updated:
            self.write(cr, uid, order.id, {'need_to_update': False})
        cr.commit() #Ugly we should not commit in the current cursor
        return True

########################################################################################################################
#
#           CODE THAT CLEAN MAGENTO DATA BEFORE IMPORTING IT THE BEST WILL BE TO REFACTOR MAGENTO API
#
########################################################################################################################


    def _merge_sub_items(self, cr, uid, product_type, top_item, child_items, context=None):
        """
        Manage the sub items of the magento sale order lines. A top item contains one
        or many child_items. For some product types, we want to merge them in the main
        item, or keep them as order line.

        This method has to stay because it allow to customize the behavior of the sale
        order according to the product type.

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

    def clean_magento_items(self, cr, uid, resource, context=None):
        """
        Method that clean the sale order line given by magento before importing it

        This method has to stay here because it allow to customize the behavior of the sale
        order.

        """
        child_items = {}  # key is the parent item id
        top_items = []

        # Group the childs with their parent
        for item in resource['items']:
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

        resource['items'] = all_items
        return resource

    def clean_magento_resource(self, cr, uid, resource, context=None):
        """
        Magento copy each address in a address sale table.
        Keeping the extid of this table 'address_id' is useless because we don't need it later
        And it's dangerous because we will have various external id for the same resource and the same referential
        Getting the ext_id of the table customer address is also not posible because Magento LIE
        Indeed if a customer create a new address on fly magento will give us the default id instead of False
        So it better to NOT trust magento and not based the address on external_id
        To avoid any erreur we remove the key
        """
        for remove_key in ['customer_address_id', 'address_id']:
            for key in ['billing_address', 'shipping_address']:
                if remove_key in resource[key]: del resource[key][remove_key]

        # For really strange and unknow reason magento want to play with me and make me some joke.
        # Depending of the customer installation some time the field customer_id is equal to NONE
        # in the sale order and sometime it's equal to NONE in the address but at least the
        # the information is correct in one of this field
        # So I make this ugly code to try to fix it.
        if not resource.get('customer_id'):
            if resource['billing_address'].get('customer_id'):
                resource['customer_id'] = resource['billing_address']['customer_id']
        else:
            if not resource['billing_address'].get('customer_id'):
                resource['billing_address']['customer_id'] = resource['customer_id']
            if not resource['shipping_address'].get('customer_id'):
                resource['shipping_address']['customer_id'] = resource['customer_id']
        return resource


class sale_order_line(Model):
    _inherit = 'sale.order.line'
    _columns = {
        # Rised the precision of the sale.order.line discount field
        # from 2 to 3 digits in order to be able to have the same amount as Magento.
        # Example: Magento has a sale line of 299€ and 150€ of discount, so a line at 149€.
        # We translate it to a percent in the openerp sale order
        # With a 2 digits precision, we can have 50.17 % => 148.99 or 50.16% => 149.02.
        # Rise the digits to 3 allows to have 50.167% => 149€
        'discount': fields.float('Discount (%)', digits=(16, 3), readonly=True, states={'draft': [('readonly', False)]}),
        }

