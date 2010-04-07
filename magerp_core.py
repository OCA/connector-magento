#########################################################################
#This module intergrates Open ERP with the magento core                 #
#Core settings are stored here                                          #
#########################################################################
#                                                                       #
# Copyright (C) 2009  Sharoon Thomas                                    #
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
from base_external_referentials import external_osv

DEBUG = True
TIMEOUT = 2
        
class external_referential(magerp_osv.magerp_osv):
    #This class stores instances of magento to which the ERP will connect, the concept of multi website, multistore integration?
    _inherit = "external.referential"

    _columns = {
        'attribute_sets':fields.one2many('magerp.product_attribute_set', 'referential_id', 'Attribute Sets'),
        'default_pro_cat':fields.many2one('product.category','Default Product Category',required=True, help="Products imported from magento may have many categories.\nOpenERP requires a specific category for a product to facilitate invoicing etc."),
        'default_lang_id':fields.many2one('res.lang', 'Default Language',required=True, help="Choose the language which will be used for the Default Value in Magento"),
    }

             
    def connect(self, cr, uid, ids, ctx={}):#TODO used?
        #ids has to be a list
        if ids:
            if len(ids) == 1:
                instance = self.browse(cr, uid, ids, ctx)[0]
                if instance:
                    core_imp_conn = self.external_connection(cr, uid, instance, DEBUG)
                    if core_imp_conn.connect():
                        return core_imp_conn

    def core_sync(self, cr, uid, ids, ctx={}):
        instances = self.browse(cr, uid, ids, ctx)
        filter = []
        for inst in instances:
            core_imp_conn = self.external_connection(cr, uid, inst, DEBUG)
            if core_imp_conn:
                self.pool.get('external.shop.group').mage_import_base(cr, uid,core_imp_conn, inst.id, defaults={'referential_id':inst.id})
                self.pool.get('sale.shop').mage_import_base(cr, uid, core_imp_conn, inst.id, defaults={'magento_shop':True})
                self.pool.get('magerp.storeviews').mage_import_base(cr,uid,core_imp_conn, inst.id, defaults={})
            else:
                osv.except_osv(_("Connection Error"), _("Could not connect to server\nCheck location, username & password."))
        return True

    def sync_categs(self, cr, uid, ids, ctx):
        instances = self.browse(cr, uid, ids, ctx)
        for inst in instances:
            pro_cat_conn = self.external_connection(cr, uid, inst, DEBUG)
            if pro_cat_conn:
                confirmation = pro_cat_conn.call('catalog_category.currentStore', [0])   #Set browse to root store
                if confirmation:
                    categ_tree = pro_cat_conn.call('catalog_category.tree')             #Get the tree
                    self.pool.get('product.category').record_entire_tree(cr, uid, inst.id, pro_cat_conn, categ_tree, DEBUG)
                    #exp_ids = self.pool.get('product.category').search(cr,uid,[('exportable','=',True)])
                    #self.pool.get('product.category').ext_export(cr,uid,exp_ids,[inst.id],{},{'conn_obj':pro_cat_conn})
            else:
                osv.except_osv(_("Connection Error"), _("Could not connect to server\nCheck location, username & password."))
        return True

    def sync_attribs(self, cr, uid, ids, ctx):
        instances = self.browse(cr, uid, ids, ctx)
        for inst in instances:
            attr_conn = self.external_connection(cr, uid, inst, DEBUG)
            if attr_conn:
                attrib_set_ids = self.pool.get('magerp.product_attribute_set').search(cr, uid, [('referential_id', '=', inst.id)])
                attrib_sets = self.pool.get('magerp.product_attribute_set').read(cr, uid, attrib_set_ids, ['magento_id'])
                #Get all attribute set ids to get all attributes in one go
                all_attr_set_ids = self.pool.get('magerp.product_attribute_set').get_all_mage_ids(cr, uid, [], inst.id)
                #Call magento for all attributes
                mage_inp = attr_conn.call('ol_catalog_product_attribute.list', all_attr_set_ids)             #Get the tree
                #self.pool.get('magerp.product_attributes').sync_import(cr, uid, mage_inp, inst.id, DEBUG) #Last argument is extra mage2oe filter as same attribute ids
                self.pool.get('magerp.product_attributes').ext_import(cr, uid, mage_inp, inst.id, defaults={'referential_id':inst.id}, context={'referential_id':inst.id})
                #Relate attribute sets & attributes
                mage_inp = {}
                #Pass in {attribute_set_id:{attributes},attribute_set_id2:{attributes}}
                #print "Attribute sets are:", attrib_sets
                for each in attrib_sets:
                    mage_inp[each['magento_id']] = attr_conn.call('ol_catalog_product_attribute.relations', [each['magento_id']])
                if mage_inp:
                    self.pool.get('magerp.product_attribute_set').relate(cr, uid, mage_inp, inst.id, DEBUG)
            else:
                osv.except_osv(_("Connection Error"), _("Could not connect to server\nCheck location, username & password."))
        return True

    def sync_attrib_sets(self, cr, uid, ids, ctx):
        instances = self.browse(cr, uid, ids, ctx)
        for inst in instances:
            attr_conn = self.external_connection(cr, uid, inst, DEBUG)
            if attr_conn:
                filter = []
                self.pool.get('magerp.product_attribute_set').mage_import_base(cr, uid, attr_conn, inst.id,{'referential_id':inst.id},{'ids_or_filter':filter})
            else:
                osv.except_osv(_("Connection Error"), _("Could not connect to server\nCheck location, username & password."))          
        return True

    def sync_attrib_groups(self, cr, uid, ids, ctx):
        instances = self.browse(cr, uid, ids, ctx)
        for inst in instances:
            attr_conn = self.external_connection(cr, uid, inst, DEBUG)
            attrset_ids = self.pool.get('magerp.product_attribute_set').get_all_mage_ids(cr, uid, [], inst.id)
            filter = [{'attribute_set_id':{'in':attrset_ids}}]
            if attr_conn:
                self.pool.get('magerp.product_attribute_groups').mage_import_base(cr, uid, attr_conn, inst.id, {'referential_id': inst.id}, {'ids_or_filter':filter})
            else:
                osv.except_osv(_("Connection Error"), _("Could not connect to server\nCheck location, username & password."))
        return True

    def sync_customer_groups(self, cr, uid, ids, ctx):
        instances = self.browse(cr, uid, ids, ctx)
        for inst in instances:
            attr_conn = self.external_connection(cr, uid, inst, DEBUG)
            filter = []
            if attr_conn:
                self.pool.get('res.partner.category').mage_import_base(cr, uid, attr_conn, inst.id, {}, {'ids_or_filter':filter})
            else:
                osv.except_osv(_("Connection Error"), _("Could not connect to server\nCheck location, username & password."))
        return True

    def sync_customer_addresses(self, cr, uid, ids, ctx):
        instances = self.browse(cr, uid, ids, ctx)
        for inst in instances:
            attr_conn = self.external_connection(cr, uid, inst, DEBUG)
            filter = []
            if attr_conn:
                #self.pool.get('res.partner').mage_import(cr, uid, filter, attr_conn, inst.id, DEBUG)
                #TODO fix by retrieving customer list first
                self.pool.get('res.partner.address').mage_import_base(cr, uid, attr_conn, inst.id, {}, {'ids_or_filter':filter})
            else:
                osv.except_osv(_("Connection Error"), _("Could not connect to server\nCheck location, username & password."))
        return True

    def sync_products(self, cr, uid, ids, ctx):
        instances = self.browse(cr, uid, ids, ctx)
        for inst in instances:
            attr_conn = self.external_connection(cr, uid, inst, DEBUG)
            filter = []
            if attr_conn:
                list_prods = attr_conn.call('catalog_product.list')
                #self.pool.get('product.product').mage_import(cr, uid, filter, attr_conn, inst.id, DEBUG)
                result = []
                for each in list_prods:
                    each_product_info = attr_conn.call('catalog_product.info', [each['product_id']])
                    result.append(each_product_info)
                self.pool.get('product.product').ext_import(cr, uid, result, inst.id, context={})
            else:
                osv.except_osv(_("Connection Error"), _("Could not connect to server\nCheck location, username & password."))
        return True

    def export_products(self, cr, uid, ids, ctx):
        shop_ids = self.pool.get('sale.shop').search(cr, uid, [])
        for inst in self.browse(cr, uid, ids, ctx):
            for shop in self.pool.get('sale.shop').browse(cr, uid, shop_ids, ctx):
                ctx['conn_obj'] = self.external_connection(cr, uid, inst)
                #shop.export_catalog
                print "cr, uid, shop, ctx", cr, uid, shop, ctx
                shop.export_products(cr, uid, shop, ctx)
        return True

external_referential()


class external_shop_group(magerp_osv.magerp_osv):
    _inherit = "external.shop.group"
    #Return format of API:{'code': 'base', 'name': 'Main', 'website_id': '1', 'is_default': '1', 'sort_order': '0', 'default_group_id': '1'}
    # default_group_id is the default shop of the external_shop_group (external_shop_group = website)

    def _get_default_shop_id(self, cr, uid, ids, prop, unknow_none, context):
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
        'is_default':fields.boolean('Is Active?'),
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
