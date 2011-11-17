# -*- encoding: utf-8 -*-
#########################################################################
#This module intergrates Open ERP with the magento core                 #
#Core settings are stored here                                          #
#########################################################################
#                                                                       #
# Copyright (C) 2009  Sharoon Thomas                                    #
# Copyright (C) 2011 Akretion Sébastien BEAU sebastien.beau@akretion.com#
# Copyright (C) 2011 Camptocamp Guewen Baconnier                        #
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
import pooler
import netsvc
from magerp_osv import Connection
import tools
from tools.translate import _

DEBUG = True
TIMEOUT = 2

class external_referential(magerp_osv.magerp_osv):
    #This class stores instances of magento to which the ERP will connect, so you can connect OpenERP to multiple Magento installations (eg different Magento databases)
    _inherit = "external.referential"

    def _is_magento_referential(self, cr, uid, ids, field_name, arg, context=None):
        """If at least one shop is magento, we consider that the external
        referential is a magento referential
        """
        res = {}
        for referential in self.browse(cr, uid, ids, context):
            res[referential.id] = False
            for group in referential.shop_group_ids:
                for shop in group.shop_ids:
                    if shop.magento_shop:
                        res[referential.id] = True
                        break
                if res[referential.id]:
                    break
        return res

    _columns = {
        'attribute_sets':fields.one2many('magerp.product_attribute_set', 'referential_id', 'Attribute Sets'),
        'default_pro_cat':fields.many2one('product.category','Default Product Category', help="Products imported from magento may have many categories.\nOpenERP requires a specific category for a product to facilitate invoicing etc."),
        'default_lang_id':fields.many2one('res.lang', 'Default Language', help="Choose the language which will be used for the Default Value in Magento"),
        'active': fields.boolean('Active'),
        'magento_referential': fields.function(_is_magento_referential, type="boolean", method=True, string="Magento Referential"),
        'last_imported_product_id': fields.integer('Last Imported Product Id', help="Product are imported one by one. This is the magento id of the last product imported. If you clear it all product will be imported"),
    }

    _defaults = {
        'active': lambda *a: 1,
    }

    def external_connection(self, cr, uid, id, DEBUG=False):
        if isinstance(id, list):
            id=id[0]
        referential = self.browse(cr, uid, id)
        if 'magento' in referential.type_id.name.lower():
            attr_conn = Connection(referential.location, referential.apiusername, referential.apipass, DEBUG)
            return attr_conn.connect() and attr_conn or False
        else:
            return super(external_referential, self).external_connection(cr, uid, referential, DEBUG=DEBUG)

    def connect(self, cr, uid, id, context=None):
        if isinstance(id, (list, tuple)):
            if not len(id) == 1:
                raise osv.except_osv(_("Error"), _("Connect should be only call with one id"))
            else:
                id = id[0]
            core_imp_conn = self.external_connection(cr, uid, id, DEBUG)
            if core_imp_conn.connect():
                return core_imp_conn
            else:
                raise osv.except_osv(_("Connection Error"), _("Could not connect to server\nCheck location, username & password."))

        return False

    def core_sync(self, cr, uid, ids, context=None):
        filter = []
        for referential_id in ids:
            core_imp_conn = self.external_connection(cr, uid, referential_id, DEBUG)
            self.pool.get('external.shop.group').mage_import_base(cr, uid,core_imp_conn, referential_id, defaults={'referential_id':referential_id})
            self.pool.get('sale.shop').mage_import_base(cr, uid, core_imp_conn, referential_id, {'magento_shop':True, 'company_id':self.pool.get('res.users').browse(cr, uid, uid).company_id.id})
            self.pool.get('magerp.storeviews').mage_import_base(cr,uid,core_imp_conn, referential_id, defaults={})
        return True

    def sync_categs(self, cr, uid, ids, context=None):
        for referential_id in ids:
            pro_cat_conn = self.external_connection(cr, uid, referential_id, DEBUG)
            confirmation = pro_cat_conn.call('catalog_category.currentStore', [0])   #Set browse to root store
            if confirmation:
                categ_tree = pro_cat_conn.call('catalog_category.tree')             #Get the tree
                self.pool.get('product.category').record_entire_tree(cr, uid, referential_id, pro_cat_conn, categ_tree, DEBUG)
                #exp_ids = self.pool.get('product.category').search(cr,uid,[('exportable','=',True)])
                #self.pool.get('product.category').ext_export(cr,uid,exp_ids,[referential_id],{},{'conn_obj':pro_cat_conn})
        return True

    def sync_attribs(self, cr, uid, ids, context=None):
        for referential_id in ids:
            attr_conn = self.external_connection(cr, uid, referential_id, DEBUG)
            attrib_set_ids = self.pool.get('magerp.product_attribute_set').search(cr, uid, [('referential_id', '=', referential_id)])
            attrib_sets = self.pool.get('magerp.product_attribute_set').read(cr, uid, attrib_set_ids, ['magento_id'])
            #Get all attribute set ids to get all attributes in one go
            all_attr_set_ids = self.pool.get('magerp.product_attribute_set').get_all_mage_ids(cr, uid, [], referential_id)
            #Call magento for all attributes
            mage_inp = attr_conn.call('ol_catalog_product_attribute.list', [all_attr_set_ids])             #Get the tree
            #self.pool.get('magerp.product_attributes').sync_import(cr, uid, mage_inp, referential_id, DEBUG) #Last argument is extra mage2oe filter as same attribute ids
            self.pool.get('magerp.product_attributes').ext_import(cr, uid, mage_inp, referential_id, defaults={'referential_id':referential_id}, context={'referential_id':referential_id})
            #Relate attribute sets & attributes
            mage_inp = {}
            #Pass in {attribute_set_id:{attributes},attribute_set_id2:{attributes}}
            #print "Attribute sets are:", attrib_sets
            for each in attrib_sets:
                mage_inp[each['magento_id']] = attr_conn.call('ol_catalog_product_attribute.relations', [each['magento_id']])
            if mage_inp:
                self.pool.get('magerp.product_attribute_set').relate(cr, uid, mage_inp, referential_id, DEBUG)
        return True

    def sync_attrib_sets(self, cr, uid, ids, context=None):
        for referential_id in ids:
            attr_conn = self.external_connection(cr, uid, referential_id, DEBUG)
            filter = []
            self.pool.get('magerp.product_attribute_set').mage_import_base(cr, uid, attr_conn, referential_id,{'referential_id':referential_id},{'ids_or_filter':filter})
        return True

    def sync_attrib_groups(self, cr, uid, ids, context=None):
        for referential_id in ids:
            attr_conn = self.external_connection(cr, uid, referential_id, DEBUG)
            attrset_ids = self.pool.get('magerp.product_attribute_set').get_all_mage_ids(cr, uid, [], referential_id)
            filter = [{'attribute_set_id':{'in':attrset_ids}}]
            self.pool.get('magerp.product_attribute_groups').mage_import_base(cr, uid, attr_conn, referential_id, {'referential_id': referential_id}, {'ids_or_filter':filter})
        return True

    def sync_customer_groups(self, cr, uid, ids, context=None):
        for referential_id in ids:
            attr_conn = self.external_connection(cr, uid, referential_id, DEBUG)
            filter = []
            self.pool.get('res.partner.category').mage_import_base(cr, uid, attr_conn, referential_id, {}, {'ids_or_filter':filter})
        return True

    def sync_customer_addresses(self, cr, uid, ids, context=None):
        for referential_id in ids:
            attr_conn = self.external_connection(cr, uid, referential_id, DEBUG)
            filter = []
            #self.pool.get('res.partner').mage_import(cr, uid, filter, attr_conn, referential_id, DEBUG)
            #TODO fix by retrieving customer list first
            self.pool.get('res.partner.address').mage_import_base(cr, uid, attr_conn, referential_id, {}, {'ids_or_filter':filter})
        return True

    def sync_products(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
#        context.update({'dont_raise_error': True})
        referentials = self.browse(cr, uid, ids, context)
        for referential in referentials:
            attr_conn = referential.external_connection(DEBUG)
            filter = []
            if referential.last_imported_product_id:
                filter.append({'product_id' : {'gt': referential.last_imported_product_id}})
            list_prods = attr_conn.call('catalog_product.list', filter)
            storeview_obj = self.pool.get('magerp.storeviews')
            lang_obj = self.pool.get('res.lang')
            #get all referential storeviews
            storeview_ids = []
            for website in referential.shop_group_ids:
                for shop in website.shop_ids:
                    for storeview in shop.storeview_ids:
                        storeview_ids += [storeview.id]

            lang_2_storeview={}
            for storeview in storeview_obj.browse(cr, uid, storeview_ids, context):
                #get lang of the storeview
                lang_id = storeview.lang_id
                if lang_id:
                    lang = lang_id.code
                else:
                    osv.except_osv(_('Warning!'), _('The storeviews have no language defined'))
                    lang = referential.default_lang_id.code
                if not lang_2_storeview.get(lang, False):
                    lang_2_storeview[lang]=storeview.code

            import_cr = pooler.get_db(cr.dbname).cursor()
            for each in list_prods:
                for lang in lang_2_storeview:
                    product_info = attr_conn.call('catalog_product.info', [each['product_id'], lang_2_storeview[lang]])
                    context['magento_sku'] = product_info['sku']
                    ctx = context.copy()
                    ctx['lang'] = lang
                    self.pool.get('product.product').ext_import(import_cr, uid, [product_info], referential.id, defaults={}, context=ctx)

                self.write(import_cr, uid, referential.id, {'last_imported_product_id': int(each['product_id'])}, context=context)
                import_cr.commit()
            import_cr.close()
        return True

    def sync_images(self, cr, uid, ids, context=None):
        logger = netsvc.Logger()
        shop_ids = self.pool.get('sale.shop').search(cr, uid, [])
        for referential in self.browse(cr, uid, ids, context):
            for shop_group in referential.shop_group_ids:
                for shop in shop_group.shop_ids:
                    conn = referential.external_connection()
                    for product in shop.exportable_product_ids:
                        try:
                            img_list = conn.call('catalog_product_attribute_media.list', [product.magento_sku])

                        except Exception, e:
                            self.log(cr, uid, product.id, "failed to find product with sku %s for product id %s in Magento!" % (product.magento_sku, product.id,))
                            logger.notifyChannel('ext synchro', netsvc.LOG_DEBUG, "failed to find product with sku %s for product id %s in Magento!" % (product.magento_sku, product.id,))
                            continue
                        logger.notifyChannel('ext synchro', netsvc.LOG_INFO, "Magento image for SKU %s: %s" %(product.magento_sku, img_list))
                        for image in img_list:
                            data = {'name': image['label'] or os.path.splitext(os.path.split(image['file'])[1])[0],
                                'link': True,
                                'filename': image['url'],
                                'product_id': product.id,
                                'base_image': image['types'].count('image') == 1,
                                'small_image': image['types'].count('small_image') == 1,
                                'thumbnail': image['types'].count('thumbnail') == 1,
                                'exclude': image['exclude'],
                                'position': image['position']
                                }
                            image_ext_name_obj = self.pool.get('product.images.external.name')
                            image_ext_name_id = image_ext_name_obj.search(cr, uid, [('name', '=', image['file']), ('external_referential_id', '=', referential.id)], context=context)
                            if image_ext_name_id:
                                # update existing image
                                # find the correspondent product image from the external name
                                image_ext_name = image_ext_name_obj.read(cr, uid, image_ext_name_id, [], context=context)
                                if self.pool.get('product.images').search(cr, uid, [('id', '=', image_ext_name[0]['id'])], context=context):
                                    self.pool.get('product.images').write(cr, uid, image_ext_name[0]['id'], data, context=context)
                                    image_ext_name_obj.write(cr, uid, image_ext_name_id, {'name':image['file']}, context=context)
                                else:
                                    self.log(cr, uid, product.id, "failed to find product image with id %s for product id %s in OpenERP!" % (image_ext_name_id, product.id,))
                                    logger.notifyChannel('ext synchro', netsvc.LOG_DEBUG, "failed to find product image with id %s for product id %s in OpenERP!" % (image_ext_name_id, product.id,))
                                    continue
                            else:
                                # create new image
                                new_image_id = self.pool.get('product.images').create(cr, uid, data, context=context)
                                image_ext_name_obj.create(cr, uid, {'name':image['file'], 'external_referential_id' : referential.id, 'image_id' : new_image_id}, context=context)
                return True

    def sync_product_links(self, cr, uid, ids, context=None):
        if context is None: context = {}
        for referential in self.browse(cr, uid, ids, context):
            conn = referential.external_connection(DEBUG)
            ctx = context.copy()
            ctx['conn'] = conn
            link_types = conn.call('catalog_product_link.types')

            exportable_product_ids= []
            for shop_group in referential.shop_group_ids:
                for shop in shop_group.shop_ids:
                    exportable_product_ids.extend([product.id for product in shop.exportable_product_ids])
            exportable_product_ids = list(set(exportable_product_ids))
            self.pool.get('product.product').mag_import_product_links(cr, uid, exportable_product_ids, link_types, referential.id, context=ctx)
        return True

    def export_products(self, cr, uid, ids, context=None):
        if context is None: context = {}
        shop_ids = self.pool.get('sale.shop').search(cr, uid, [])
        for referential_id in ids:
            for shop in self.pool.get('sale.shop').browse(cr, uid, shop_ids, context):
                context['conn_obj'] = self.external_connection(cr, uid, referential_id)
                #shop.export_catalog
                tools.debug((cr, uid, shop, context,))
                shop.export_products(cr, uid, shop, context)
        return True

    def sync_partner(self, cr, uid, ids, context=None):
        for referential_id in ids:
            attr_conn = self.external_connection(cr, uid, referential_id, DEBUG)
            result = []
            result_address = []

            list_customer = attr_conn.call('customer.list')

            for each in list_customer:
                customer_id = int(each['customer_id'])

                each_customer_info = attr_conn.call('customer.info', [customer_id])
                result.append(each_customer_info)

                each_customer_address_info = attr_conn.call('customer_address.list', [customer_id])
                if len(each_customer_address_info):
                    customer_address_info = each_customer_address_info[0]
                    customer_address_info['customer_id'] = customer_id
                    customer_address_info['email'] = each_customer_info['email']
                    result_address.append(customer_address_info)
                    print customer_address_info

            partner_ids = self.pool.get('res.partner').ext_import(cr, uid, result, referential_id, context={})
            if result_address:
                partner_address_ids = self.pool.get('res.partner.address').ext_import(cr, uid, result_address, referential_id, context={})

        return True

    def sync_newsletter(self, cr, uid, ids, context=None):
        #update first all customer
        self.sync_partner(cr, uid, ids, context)

        partner_obj = self.pool.get('res.partner')

        for referential_id in ids:
            attr_conn = self.external_connection(cr, uid, referential_id, DEBUG)
            filter = []
            list_subscribers = attr_conn.call('ol_customer_subscriber.list')
            result = []
            for each in list_subscribers:
                each_subscribers_info = attr_conn.call('ol_customer_subscriber.info', [each])

                # search this customer. If exist, update your newsletter subscription
                partner_ids = partner_obj.search(cr, uid, [('emailid', '=', each_subscribers_info[0]['subscriber_email'])])
                if partner_ids:
                    #unsubscriber magento value: 3
                    if int(each_subscribers_info[0]['subscriber_status']) == 1:
                        subscriber_status = 1
                    else:
                        subscriber_status = 0
                    partner_obj.write(cr, uid, partner_ids[0], {'mag_newsletter': subscriber_status})
        return True

    def sync_newsletter_unsubscriber(self, cr, uid, ids, context=None):
        partner_obj = self.pool.get('res.partner')

        for referential_id in ids:
            attr_conn = self.external_connection(cr, uid, referential_id, DEBUG)
            partner_ids  = partner_obj.search(cr, uid, [('mag_newsletter', '!=', 1), ('emailid', '!=', '')])

            print partner_ids

            for partner in partner_obj.browse(cr, uid, partner_ids):
                print partner.emailid
                if partner.emailid:
                    attr_conn.call('ol_customer_subscriber.delete', [partner.emailid])

        return True

    # Schedules functions ============ #
    def run_import_newsletter_scheduler(self, cr, uid, context=None):
        if context is None:
            context = {}

        referential_ids  = self.search(cr, uid, [('active', '=', 1)])

        if referential_ids:
            self.sync_newsletter(cr, uid, referential_ids, context)
        if DEBUG:
            print "run_import_newsletter_scheduler: %s" % referential_ids

    def run_import_newsletter_unsubscriber_scheduler(self, cr, uid, context=None):
        if context is None:
            context = {}

        referential_ids  = self.search(cr, uid, [('active', '=', 1)])

        if referential_ids:
            self.sync_newsletter_unsubscriber(cr, uid, referential_ids, context)
        if DEBUG:
            print "run_import_newsletter_unsubscriber_scheduler: %s" % referential_ids

external_referential()


class external_shop_group(magerp_osv.magerp_osv):
    _inherit = "external.shop.group"
    #Return format of API:{'code': 'base', 'name': 'Main', 'website_id': '1', 'is_default': '1', 'sort_order': '0', 'default_group_id': '1'}
    # default_group_id is the default shop of the external_shop_group (external_shop_group = website)

    def _get_default_shop_id(self, cr, uid, ids, prop, unknow_none, context=None):
        res = {}
        for shop_group in self.browse(cr, uid, ids, context):
            if shop_group.default_shop_integer_id:
                rid = self.pool.get('sale.shop').extid_to_oeid(cr, uid, shop_group.default_shop_integer_id, shop_group.referential_id.id)
                res[shop_group.id] = rid
            else:
                res[shop_group.id] = False
        return res

    _columns = {
        'code':fields.char('Code', size=100),
        'is_default':fields.boolean('Is Default?'),
        'sort_order':fields.integer('Sort Order'),
        'default_shop_integer_id':fields.integer('Default Store'), #This field can't be a many2one because shop_group field will be mapped before creating Shop (Shop = Store, shop_group = website)
        'default_shop_id':fields.function(_get_default_shop_id, type="many2one", relation="sale.shop", method=True, string="Default Store"),
        'referential_type' : fields.related('referential_id', 'type_id', type='many2one', relation='external.referential.type', string='External Referential Type'),
    }

external_shop_group()


class magerp_storeviews(magerp_osv.magerp_osv):
    _name = "magerp.storeviews"
    _description = "The magento store views information"

    _columns = {
        'name':fields.char('Store View Name', size=100),
        'code':fields.char('Code', size=100),
        'website_id':fields.many2one('external.shop.group', 'Website', select=True, ondelete='cascade'),
        'is_active':fields.boolean('Default ?'),
        'sort_order':fields.integer('Sort Order'),
        'shop_id':fields.many2one('sale.shop', 'Shop', select=True, ondelete='cascade'),
        'lang_id':fields.many2one('res.lang', 'Language'),
    }

    #Return format of API:{'code': 'default', 'store_id': '1', 'website_id': '1', 'is_active': '1', 'sort_order': '0', 'group_id': '1', 'name': 'Default Store View'}

magerp_storeviews()
