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
import xmlrpclib
import netsvc
from dateutil.relativedelta import *
import time
import datetime
import urllib2
import base64
import magerp_osv

DEBUG = True
TIMEOUT = 2

class Connection():
    def __init__(self, location, username, password, debug=False):
        #Append / if not there
        if not location[-1] == '/':
            location += '/' 
        self.corelocation = location
        self.location = location + "index.php/api/xmlrpc"
        self.username = username
        self.password = password
        self.debug = debug
        self.result = {}
        self.logger = netsvc.Logger()
    
    def transform(self, subject):
        #This function will convert string objects to the data type required
        for key in subject.keys():
            if key[0:3] == "is_":
                if subject[key] == '0':
                    subject[key] = False
                else:
                    subject[key] = True
        return subject
    
    def connect(self):
        if not self.location[-1] == '/':
            self.location += '/'
        if self.debug:
            self.logger.notifyChannel(_("Magento Connection"), netsvc.LOG_INFO, _("Attempting connection with Settings:%s,%s,%s") % (self.location, self.username, self.password))
        self.ser = xmlrpclib.ServerProxy(self.location)
        try:
            self.session = self.ser.login(self.username, self.password)
            if self.debug:
                self.logger.notifyChannel(_("Magento Connection"), netsvc.LOG_INFO, _("Login Successful"))
            return True
        except Exception, e:
            self.logger.notifyChannel(_("Magento Connection"), netsvc.LOG_ERROR, _("Error in connecting") % (e))
            return False
    
    def call(self, method, *args): 
        if args:
            arguments = list(args)[0]
        else:
            arguments=[]
        try:
            if self.debug:
                self.logger.notifyChannel(_("Magento Connection"), netsvc.LOG_INFO, _("Calling Method:%s,Arguments:%s") % (method, arguments))
            res = self.ser.call(self.session, method, arguments)
            if self.debug:
                self.logger.notifyChannel(_("Magento Connection"), netsvc.LOG_INFO, _("Query Returned:%s") % (res))
            return res
        except Exception, e:
            self.logger.notifyChannel(_("Magento Call"), netsvc.LOG_ERROR, _("Method: %s\nArguments:%s\nError:%s") % (method, arguments, e))
            raise
    
    def fetch_image(self,imgloc):
        full_loc = self.corelocation + imgloc
        try:
            img = urllib2.urlopen(full_loc)
            return base64.b64encode(img.read())
        except Exception,e:
            pass
        
class magerp_instances(osv.osv):
    #This class stores instances of magento to which the ERP will connect, the concept of multi website, multistore integration?
    _name = "magerp.instances"
    _description = "Instances of magento connected"
    _columns = {
        'name':fields.char('Instance Name', size=100, required=True),
        'location':fields.char('Base URL', size=200, help="Eg:http://thestore.com/ \nUse trailing slash", required=True),
        'apiusername':fields.char('API user name', size=100, required=True),
        'apipass':fields.char('API Password', size=100, required=True),
        'websites':fields.one2many('magerp.websites', 'instance', 'Websites'),
        'storeviews':fields.one2many('magerp.storeviews', 'instance', 'Store Views'),
        'groups':fields.one2many('magerp.groups', 'instance', 'Groups'),
        'attribute_sets':fields.one2many('magerp.product_attribute_set','instance','Attribute Sets')
    }

    def connect(self,cr,uid,ids,ctx={}):
        #ids has to be a list
        if ids:
            if len(ids)==1:
                instance = self.browse(cr, uid, ids, ctx)[0]
                if instance:
                    core_imp_conn = Connection(instance.location, instance.apiusername, instance.apipass, DEBUG)
                    if core_imp_conn.connect():
                        return core_imp_conn
        return False
   
    def core_sync(self, cr, uid, ids, ctx={}):
        instances = self.browse(cr, uid, ids, ctx)
        filter = []
        for inst in instances:
            core_imp_conn = Connection(inst.location, inst.apiusername, inst.apipass, DEBUG)
            if core_imp_conn.connect():
                #New import methods
                self.pool.get('magerp.websites').mage_import(cr,uid,filter,core_imp_conn,inst.id,DEBUG)
                self.pool.get('magerp.storeviews').mage_import(cr,uid,filter,core_imp_conn,inst.id,DEBUG)
                self.pool.get('magerp.groups').mage_import(cr,uid,filter,core_imp_conn,inst.id,DEBUG)
            else:
                osv.except_osv(_("Connection Error"), _("Could not connect to server\nCheck location, username & password."))
    
    def sync_categs(self,cr,uid,ids,ctx):
        instances = self.browse(cr, uid, ids, ctx)
        for inst in instances:
            pro_cat_conn = Connection(inst.location, inst.apiusername, inst.apipass, DEBUG)
            if pro_cat_conn.connect():
                confirmation = pro_cat_conn.call('catalog_category.currentStore',[0])   #Set browse to root store
                if confirmation:
                    categ_tree = pro_cat_conn.call('catalog_category.tree')             #Get the tree
                    self.pool.get('product.category').record_entire_tree(cr,uid,inst.id,pro_cat_conn,categ_tree)
            else:
                osv.except_osv(_("Connection Error"), _("Could not connect to server\nCheck location, username & password."))
    
    def sync_attribs(self,cr,uid,ids,ctx):
        instances = self.browse(cr, uid, ids, ctx)
        for inst in instances:
            attr_conn = Connection(inst.location, inst.apiusername, inst.apipass, DEBUG)
            if attr_conn.connect():
                attrib_set_ids = self.pool.get('magerp.product_attribute_set').search(cr,uid,[('instance','=',inst.id)])
                attrib_sets = self.pool.get('magerp.product_attribute_set').read(cr,uid,attrib_set_ids,['attribute_set_id'])
                #Get all attribute set ids to get all attributes in one go
                all_attr_set_ids=self.pool.get('magerp.product_attribute_set').getall_mageids(cr,uid,[],inst.id)
                #Call magento for all attributes
                mage_inp = attr_conn.call('catalog_product_attribute.list',all_attr_set_ids)             #Get the tree
                self.pool.get('magerp.product_attributes').sync_import(cr,uid,mage_inp,inst.id,DEBUG) #Last argument is extra mage2oe filter as same attribute ids
                #Relate attribute sets & attributes
                mage_inp = {}
                #Pass in {attribute_set_id:{attributes},attribute_set_id2:{attributes}}
                for each in attrib_sets:
                    mage_inp[each['attribute_set_id']] = attr_conn.call('ol_catalog_product_attribute.relations',[each['attribute_set_id']])
                if mage_inp:
                    self.pool.get('magerp.product_attribute_set').relate(cr,uid,mage_inp,inst.id,DEBUG)
            else:
                osv.except_osv(_("Connection Error"), _("Could not connect to server\nCheck location, username & password."))
            
                
    
    def sync_attrib_sets(self,cr,uid,ids,ctx):
        instances = self.browse(cr, uid, ids, ctx)
        for inst in instances:
            attr_conn = Connection(inst.location, inst.apiusername, inst.apipass, DEBUG)
            if attr_conn.connect():
                filter = []
                self.pool.get('magerp.product_attribute_set').mage_import(cr,uid,filter,attr_conn,inst.id,DEBUG)
            else:
                osv.except_osv(_("Connection Error"), _("Could not connect to server\nCheck location, username & password."))          
    
    def sync_attrib_groups(self,cr,uid,ids,ctx):
        instances = self.browse(cr, uid, ids, ctx)
        for inst in instances:
            attr_conn = Connection(inst.location, inst.apiusername, inst.apipass, DEBUG)
            attrset_ids = self.pool.get('magerp.product_attribute_set').getall_mageids(cr,uid,[],inst.id)
            filter = [{'attribute_set_id':{'in':attrset_ids}}]
            if attr_conn.connect():
                self.pool.get('magerp.product_attribute_groups').mage_import(cr,uid,filter,attr_conn,inst.id,DEBUG)
            else:
                osv.except_osv(_("Connection Error"), _("Could not connect to server\nCheck location, username & password."))
    
    def sync_customer_groups(self,cr,uid,ids,ctx):
        instances = self.browse(cr, uid, ids, ctx)
        for inst in instances:
            attr_conn = Connection(inst.location, inst.apiusername, inst.apipass, DEBUG)
            filter = []
            if attr_conn.connect():
                self.pool.get('res.partner.category').mage_import(cr,uid,filter,attr_conn,inst.id,DEBUG)
            else:
                osv.except_osv(_("Connection Error"), _("Could not connect to server\nCheck location, username & password."))
    
    def sync_customer_addresses(self,cr,uid,ids,ctx):
        instances = self.browse(cr, uid, ids, ctx)
        for inst in instances:
            attr_conn = Connection(inst.location, inst.apiusername, inst.apipass, DEBUG)
            filter = []
            if attr_conn.connect():
                self.pool.get('res.partner').mage_import(cr,uid,filter,attr_conn,inst.id,DEBUG)
            else:
                osv.except_osv(_("Connection Error"), _("Could not connect to server\nCheck location, username & password."))
    
    def sync_products(self,cr,uid,ids,ctx):
        instances = self.browse(cr, uid, ids, ctx)
        for inst in instances:
            attr_conn = Connection(inst.location, inst.apiusername, inst.apipass, DEBUG)
            filter = []
            if attr_conn.connect():
                self.pool.get('magerp.product_product').mage_import(cr,uid,filter,attr_conn,inst.id,DEBUG)
            else:
                osv.except_osv(_("Connection Error"), _("Could not connect to server\nCheck location, username & password."))                        
                                
magerp_instances()

class magerp_websites(magerp_osv.magerp_osv):
    _name = "magerp.websites"
    _description = "The magento websites information"
    _MAGE_FIELD = 'website_id'
    _LIST_METHOD = 'ol_websites.list'
    #Return format of API:{'code': 'base', 'name': 'Main', 'website_id': '1', 'is_default': '1', 'sort_order': '0', 'default_group_id': '1'}
            
    def _get_group(self, cr, uid, ids, prop, unknow_none, context):
        res = self.group_get(cr, uid, ids, context={'field':'default_group_id'})
        return dict(res)        

    _order = 'website_id'
    
    _columns = {
        'name':fields.char('Website Name', size=100),
        'code':fields.char('Code', size=100),
        'website_id':fields.integer('Website ID'),
        'is_default':fields.boolean('Is Active?'),
        'sort_order':fields.integer('Sort Order'),
        'default_group_id':fields.integer('Default Store Group'), #Many 2 one?
        'default_group':fields.function(_get_group, type="many2one", relation="magerp.groups", method=True, string="Default Store (Group)"),
        'instance':fields.many2one('magerp.instances', 'Instance',ondelete='cascade')
    }
    _mapping = {
        'name':('name',str),
        'code':('code',str),
        'website_id':('website_id',int),
        'is_default':('is_default',bool),
        'sort_order':('sort_order',int),
        'default_group_id':('default_group_id',int), #Many 2 one?
               
    }


magerp_websites()

class magerp_storeviews(magerp_osv.magerp_osv):
    _name = "magerp.storeviews"
    _description = "The magento store views information"
       
    def _get_website(self, cr, uid, ids, prop, unknow_none, context):
        res = self.website_get(cr, uid, ids, context={'field':'website_id'})
        return dict(res)
    
    def _get_group(self, cr, uid, ids, prop, unknow_none, context):
        res = self.group_get(cr, uid, ids, context={'field':'group_id'})
        return dict(res) 
    
    _order = 'store_id'
    _MAGE_FIELD = 'store_id'
    _LIST_METHOD = 'ol_storeviews.list'
    _columns = {
        'name':fields.char('Store View Name', size=100),
        'code':fields.char('Code', size=100),
        'store_id':fields.integer('Store ID'),
        'website_id':fields.integer('Website'), # Many 2 one ?
        'website':fields.function(_get_website, type="many2one", relation="magerp.websites", method=True, string="Website"),
        'is_active':fields.boolean('Default ?'),
        'sort_order':fields.integer('Sort Order'),
        'group_id':fields.integer('Default Store Group'), #Many 2 one?
        'default_group':fields.function(_get_group, type="many2one", relation="magerp.groups", method=True, string="Default Store (Group)"),
        'instance':fields.many2one('magerp.instances', 'Instance',ondelete='cascade')
    }
    _mapping = {
        'name':('name',str),
        'code':('code',str),
        'store_id':('store_id',int),
        'website_id':('website_id',int), # Many 2 one ?
        'is_active':('is_active',bool),
        'sort_order':('sort_order',int),
        'group_id':('group_id'), #Many 2 one?
    
    }
    #Return format of API:{'code': 'default', 'store_id': '1', 'website_id': '1', 'is_active': '1', 'sort_order': '0', 'group_id': '1', 'name': 'Default Store View'}


magerp_storeviews()

class magerp_groups(magerp_osv.magerp_osv):
    _name = "magerp.groups"
    _description = "The magento groups(store) information"
       
    def _get_website(self, cr, uid, ids, prop, unknow_none, context):
        res = self.website_get(cr, uid, ids, context={'field':'website_id'})
        return dict(res) 
   
    def _get_store(self, cr, uid, ids, prop, unknow_none, context):
        res = self.store_get(cr, uid, ids, context={'field':'default_store_id'})
        return dict(res)     

    def rootcategory_get(self, cr, uid, ids, context=None):
        if not len(ids):
            return []
        reads = self.read(cr, uid, ids, ['root_category_id','instance'], context)
        res = []
        for record in reads:
            rid = self.pool.get('product.category').mage_to_oe(cr, uid, record['root_category_id'],record['instance'][0])
            res.append((record['id'], rid))
        return res
    
    def _get_rootcategory(self, cr, uid, ids, prop, unknow_none, context):
        res = self.rootcategory_get(cr, uid, ids, context)
        return dict(res)     
       
    _order = 'group_id'
    _MAGE_FIELD = 'group_id'
    _LIST_METHOD = 'ol_groups.list'
    _columns = {
        'name':fields.char('Store(Group) Name', size=100),
        'group_id':fields.integer('ID'),
        'default_store_id':fields.integer('Store ID'), #Many 2 one ?
        'default_store':fields.function(_get_store, type="many2one", relation="magerp.storeviews", method=True, string="Store View"),
        'website_id':fields.integer('Website'), # Many 2 one ?
        'website':fields.function(_get_website, type="many2one", relation="magerp.websites", method=True, string="Website"),
        'root_category_id':fields.integer('Root product Category'),
        'root_category':fields.function(_get_rootcategory, type="many2one", relation="product.category", method=True, string="Root Category"),
        'instance':fields.many2one('magerp.instances', 'Instance',ondelete='cascade')
    }
    _mapping = {
        'name':('name',str),
        'group_id':('group_id',int),
        'default_store_id':('default_store_id',int), #Many 2 one ?
        'website_id':('website_id',int), # Many 2 one ?
        'root_category_id':('root_category_id',int),
    }
    #Return format of API:{'default_store_id': '1', 'group_id': '1', 'website_id': '1', 'name': 'Main Website Store', 'root_category_id': '2'

magerp_groups()
