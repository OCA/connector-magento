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
#from logilab.astng.nodes import try_except_block_range
from compiler.ast import TryFinally
import datetime
import base64
import time
import magerp_osv
from tools.translate import _
import netsvc


class product_category(magerp_osv.magerp_osv):
    _inherit = "product.category"
    
    def name_get(self, cr, uid, ids, context=None):
        if not len(ids):
            return []
        reads = self.read(cr, uid, ids, ['name', 'parent_id', 'instance'], context)
        res = []
        for record in reads:
            name = record['name']
            if record['parent_id']:
                name = record['parent_id'][1] + ' / ' + name
            if record['instance'] and not record['parent_id']:
                name = "[" + record['instance'][1] + "] " + name 
            res.append((record['id'], name))
        return res

    def _name_get_fnc(self, cr, uid, ids, prop, unknow_none, context):
        res = self.name_get(cr, uid, ids, context)
        return dict(res)
    
    def ext_create(self, cr, uid, data, conn, method, oe_id, context):
        return conn.call(method, [data.get('parent_id', 1), data])
    
    _columns = {
        'create_date': fields.datetime('Created date', readonly=True),
        'write_date': fields.datetime('Updated date', readonly=True),
        'exportable':fields.boolean('Export to Magento'),
        'updated':fields.boolean('To synchronize', help="Set if the category underwent a change & has to be synched."),
        'instance':fields.many2one('external.referential', 'Magento Instance', readonly=True, store=True),
        #*************** Magento Fields ********************
        #==== General Information ====
        'magento_id': fields.integer('Magento category ID', readonly=True, help="If you have created the category from Open ERP this value will be updated once the category is exported"),
        'level': fields.integer('Level', readonly=True),
        'magento_parent_id': fields.integer('Magento Parent', readonly=True), #Key Changed from parent_id
        'is_active': fields.boolean('Active?', help="Indicates whether active in magento"),
        'description': fields.text('Description'),
        'image': fields.binary('Image'),
        'image_name':fields.char('File Name', size=100),
        'meta_title': fields.char('Title (Meta)', size=75),
        'meta_keywords': fields.text('Meta Keywords'),
        'meta_description': fields.text('Meta Description'),
        'url_key': fields.char('URL-key', size=100, readonly=True), #Readonly
        #==== Display Settings ====
        'display_mode': fields.selection([
                    ('PRODUCTS', 'Products Only'),
                    ('PAGE', 'Static Block Only'),
                    ('PRODUCTS_AND_PAGE', 'Static Block & Products')], 'Display Mode', required=True),
        'is_anchor': fields.boolean('Anchor?'),
        'available_sort_by': fields.selection([
                    ('', 'Use Config Settings'),
                    ('None', 'Use Config Settings'),
                    ('position', 'Best Value'),
                    ('name', 'Name'),
                    ('price', 'Price')
                    ], 'Available Product Listing (Sort By)'),
        'default_sort_by': fields.selection([
                    ('None', 'Use Config Settings'),
                    ('position', 'Best Value'),
                    ('name', 'Name'),
                    ('price', 'Price')
                    ], 'Default Product Listing Sort (Sort By)'),
        'magerp_stamp':fields.datetime('Magento stamp')
        }
    _defaults = {
        'display_mode':lambda * a:'PRODUCTS',
        'available_sort_by':lambda * a:'None',
        'default_sort_by':lambda * a:'None',
        'level':lambda * a:1
                 }
    
    def write(self, cr, uid, ids, vals, ctx={}):
        if not 'magerp_stamp' in vals.keys():
            vals['magerp_stamp'] = time.strftime('%Y-%m-%d %H:%M:%S')
        return super(product_category, self).write(cr, uid, ids, vals, ctx)
    
    def record_entire_tree(self, cr, uid, id, conn, categ_tree, DEBUG=False):
        self.record_category(cr, uid, id, conn, int(categ_tree['category_id']))
        for each in categ_tree['children']:
            self.record_entire_tree(cr, uid, id, conn, each)
        return True
            
    def record_category(self, cr, uid, external_referential_id, conn, category_id):
        #This function should record a category
        #The parent has to be created before creating child
        imp_vals = conn.call('category.info', [category_id])
        self.ext_import(cr, uid, [imp_vals], external_referential_id, defaults={}, context={'conn_obj':conn})
                
product_category()


class magerp_product_attributes(magerp_osv.magerp_osv):
    _name = "magerp.product_attributes"
    _description = "Attributes of products"
    _rec_name = "attribute_code"
    _LIST_METHOD = 'ol_catalog_product_attribute.list'
    
    def group_get(self, cr, uid, ids, context=None):
        if not len(ids):
            return []
        reads = self.read(cr, uid, ids, ['group_id', 'instance'], context)
        res = []
        for record in reads:
            rid = self.pool.get('magerp.product_attribute_groups').mage_to_oe(cr, uid, record['group_id'], record['instance'][0])
            if rid:
                res.append((record['id'], rid))
        return res
    
    def _get_group(self, cr, uid, ids, prop, unknow_none, context):
        res = self.group_get(cr, uid, ids, context)
        return dict(res)
    
    _columns = {
        'attribute_code':fields.char('Code', size=200),
        'magento_id':fields.integer('ID'),
        'set_id':fields.integer('Attribute Set'),
        'options':fields.one2many('magerp.product_attribute_options', 'attribute_id', 'Attribute Options'),
        #'set':fields.function(_get_set, type="many2one", relation="magerp.product_attribute_set", method=True, string="Attribute Set"), This field is invalid as attribs have m2m relation
        'frontend_input':fields.selection([
                                           ('text', 'Text'),
                                           ('textarea', 'Text Area'),
                                           ('select', 'Selection'),
                                           ('date', 'Date'),
                                           ('price', 'Price'),
                                           ('media_image', 'Media Image'),
                                           ('gallery', 'Gallery')
                                           ], 'Frontend Input'
                                          ),
        'frontend_class':fields.char('Frontend Class', size=100),
        'backend_model':fields.char('Backend Model', size=200),
        'backend_type':fields.selection([
                                         ('static', 'static'),
                                         ('varchar', ' Varchar'),
                                         ('text', 'Text'),
                                         ('decimal', 'Decimal'),
                                         ('int', 'Integer'),
                                         ('datetime', 'Datetime')], 'Backend Type'),
        'frontend_label':fields.char('Label', size=100),
        'is_visible_in_advanced_search':fields.boolean('Visible in advanced search?', required=False),
        'is_global':fields.boolean('Global ?', required=False),
        'is_filterable':fields.boolean('Filterable?', required=False),
        'is_comparable':fields.boolean('Comparable?', required=False),
        'is_visible':fields.boolean('Visible?', required=False),
        'is_searchable':fields.boolean('Searchable ?', required=False),
        'is_user_defined':fields.boolean('User Defined?', required=False),
        'is_configurable':fields.boolean('Configurable?', required=False),
        'is_visible_on_front':fields.boolean('Visible (Front)?', required=False),
        'is_used_for_price_rules':fields.boolean('Used for pricing rules?', required=False),
        'is_unique':fields.boolean('Unique?', required=False),
        'is_required':fields.boolean('Required?', required=False),
        'position':fields.integer('Position', required=False),
        'group_id': fields.integer('Group') ,
        'group':fields.function(_get_group, type="many2one", relation="magerp.product_attribute_groups", method=True, string="Attribute Group"),
        'apply_to': fields.char('Apply to', size=200),
        'default_value': fields.char('Default Value', size=10),
        'note':fields.char('Note', size=200),
        'entity_type_id':fields.integer('Entity Type'),
        'instance':fields.many2one('external.referential', 'Magento Instance', readonly=True, store=True),
        #These parameters are for automatic management
        'field_name':fields.char('Open ERP Field name', size=100)
        }
    #mapping magentofield:(openerpfield,typecast,)
    #have an entry for each mapped field
    _no_create_list = [
                        'product_id',
                        'name',
                        'description',
                        'short_description',
                        'sku',
                        'weight',
                        'category_ids',
                        'price',
                        'cost',
                        'set'
                       ]
    def create(self, cr, uid, vals, context={}):
        if not vals['attribute_code'] in self._no_create_list:
            field_name = "x_magerp_" + vals['attribute_code']
            vals['field_name'] =  field_name
        crid = super(magerp_product_attributes, self).create(cr, uid, vals, context)
        if not vals['attribute_code'] in self._no_create_list:
            #If the field has to be created
            if crid:
                #Fetch Options
                if 'frontend_input' in vals.keys() and vals['frontend_input'] in ['select']:
                    core_conn = self.pool.get('external.referential').connect(cr, uid, [vals['instance']])
                    self.pool.get('magerp.product_attribute_options').mage_import(cr, uid, [vals['magento_id']], core_conn, vals['instance'], debug=False, defaults={'attribute_id':crid})
                #Manage fields
                if vals['attribute_code']:
                    #Code for dynamically generating field name and attaching to this
                    model_id = self.pool.get('ir.model').search(cr, uid, [('model', '=', 'product.product')])
                    type_conversion = {
                            '':'char',
                            'text':'char',
                            'textarea':'text',
                            'select':'many2one',
                            'date':'date',
                            'price':'float',
                            'media_image':'binary',
                            'gallery':'binary',
                            False:'char'
                        }
                    type_casts = {
                            '':'str',
                            'text':'str',
                            'textarea':'str',
                            'select':'int',
                            'date':'str',
                            'price':'float',
                            'media_image':'False',
                            'gallery':'False',
                            False:'str'
                            }
                    if model_id and len(model_id) == 1:
                        model_id = model_id[0]
                        #Check if field already exists
                        referential_id = context.get('referential_id',False)
                        field_ids = self.pool.get('ir.model.fields').search(cr, uid, [('name', '=', field_name), ('model_id', '=', model_id)])
                        if not field_ids:
                            #The field is not there create it
                            field_vals = {
                                'name':field_name,
                                'model_id':model_id,
                                'model':'product.product',
                                'field_description':vals.get('frontend_label', False) or vals['attribute_code'],
                                'ttype':type_conversion[vals.get('frontend_input', False)],
                                          }
                            #IF char add size
                            if field_vals['ttype'] == 'char':
                                field_vals['size'] = 100
                            if field_vals['ttype'] == 'many2one':
                                field_vals['relation'] = 'magerp.product_attribute_options'
                                field_vals['domain'] = "[('attribute_id','='," + str(crid) + ")]"
                            field_vals['state'] = 'manual'
                            #All field values are computed, now save
                            field_id = self.pool.get('ir.model.fields').create(cr, uid, field_vals)
                            field_ids = [field_id]
                        #Search & create mapping entries
                        mapping_id = self.pool.get('external.mapping').search(cr, uid, [('referential_id', '=', referential_id), ('model_id', '=', model_id)])
                        if field_ids and mapping_id:
                            field_id = field_ids[0]
                            mapping_line = {
                                'external_field': vals['attribute_code'],
                                'mapping_id': mapping_id[0],
                                'type': 'in_out',
                                'external_type':type_casts[vals.get('frontend_input', False)],
                                            }
                            mapping_line['field_id'] = field_id,
                            if field_vals['ttype'] in ['char','text','date','float']:
                                mapping_line['in_function']= "result =[('" + field_name + "',ifield)]"
                            elif field_vals['ttype'] in ['many2one']:
                                mapping_line['in_function']= """if ifield:\n\toption_id = self.pool.get('magerp.product_attribute_options').search(cr,uid,[('attribute_id','=',crid),('value','=',ifield)])\n\tif option_id:\n\t\t\tresult = [('"""
                                mapping_line['in_function'] += field_name + "',ifield)]"
                            elif field_vals['ttype'] in ['binary']:
                                print "Binary mapping not done yet :("
                            self.pool.get('external.mapping.line').create(cr,uid,mapping_line)
        return crid
    
    def rebuild_view(self,cr,uid):
        print "This function is not implemented yet"
        #In the page for magento information, first create two field
        #Field 1:instance (Informational & not limiting) & Field 2:Set
        """Add field instance"""
        """Add field set"""
        #create a new notebook
        """
        for each_set attribute_set
               for each_group in attribute_set:
                    create page with attrs={'invisible':[('set','!=',each_set)]}
                    for each_mage_attribute in each_group:
                        check if field is not in _no_create_list
                            get the field_name for attribute & add it
        save the xml to form view 
        """
magerp_product_attributes()

class magerp_product_attribute_options(magerp_osv.magerp_osv):
    _name = "magerp.product_attribute_options"
    _description = "Options  of selected attributes"
    _rec_name = "label"
    _LIST_METHOD = 'ol_catalog_product_attribute.options'
    
    _columns = {
        'attribute_id':fields.many2one('magerp.product_attributes', 'Attribute'),
        'attribute_name':fields.related('attribute_id', 'attribute_code', type='char', string='Attribute Code',),
        'value':fields.char('Value', size=200),
        'ipcast':fields.char('Type cast', size=50),
        'label':fields.char('Label', size=100),
        'instance':fields.many2one('external.referential', 'Magento Instance', readonly=True, store=True),
                }
    def get_option_id(self, cr, uid, attr_name, value, instance):
        attr_id = self.search(cr, uid, [('attribute_name', '=', attr_name), ('value', '=', value), ('instance', '=', instance)])
        if attr_id:
            return attr_id[0]
        else:
            return False
magerp_product_attribute_options()

class magerp_product_attribute_set(magerp_osv.magerp_osv):
    _name = "magerp.product_attribute_set"
    _description = "Attribute sets in products"
    _rec_name = 'attribute_set_name'
    _LIST_METHOD = 'ol_catalog_product_attributeset.list'
    _columns = {
        'magento_id':fields.integer('ID'),
        'sort_order':fields.integer('Sort Order'),
        'attribute_set_name':fields.char('Set Name', size=100),
        'attributes':fields.many2many('magerp.product_attributes', 'magerp_attrset_attr_rel', 'set_id', 'attr_id', 'Attributes'),
        'instance':fields.many2one('external.referential', 'Magento Instance', readonly=True, store=True),
                }
    def relate(self, cr, uid, mage_inp, instance, *args):
        #TODO: Build the relations code
        #Note: It is better to insert multiple record by cr.execute because:
        #1. Everything ends in a sinlge query (Fast)
        #2. If the values are updated using the return value for m2m field it may execute much slower
        #3. Multirow insert is 4x faster than reduntant insert ref:http://kaiv.wordpress.com/2007/07/19/faster-insert-for-multiple-rows/
        rel_dict = {}
        #Get all attributes in onew place to convert from mage_id to oe_id
        attr_ids = self.pool.get('magerp.product_attributes').search(cr, uid, [])
        attr_list_oe = self.pool.get('magerp.product_attributes').read(cr, uid, attr_ids, ['magento_id'])
        attr_list = {}
        print attr_list_oe
        for each_set in attr_list_oe:
            attr_list[each_set['magento_id']] = each_set['id']
        attr_set_ids = self.search(cr, uid, [])
        attr_set_list_oe = self.read(cr, uid, attr_set_ids, ['magento_id'])
        attr_set_list = {}
        print attr_set_list_oe
        for each_set in attr_set_list_oe:
            attr_set_list[each_set['magento_id']] = each_set['id']
        key_attrs = []
        print mage_inp
        for each_key in mage_inp.keys():
            self.write(cr, uid, attr_set_list[each_key], {'attributes': [[6, 0, []]]})
            for each_attr in mage_inp[each_key]:
                if each_attr['attribute_id']:
                    try:
                        key_attrs.append((attr_set_list[each_key], attr_list[int(each_attr['attribute_id'])]))
                    except Exception, e:
                        pass
        #rel_dict {set_id:[attr_id_1,attr_id_2,],set_id2:[attr_id_1,attr_id_3]}
        if len(key_attrs) > 0:
            #rel_dict {set_id:[attr_id_1,attr_id_2,],set_id2:[attr_id_1,attr_id_3]}
            query = "INSERT INTO magerp_attrset_attr_rel (set_id,attr_id) VALUES "
            for each_pair in key_attrs:
                query += str(each_pair)
                query += ","
            query = query[0:len(query) - 1] + ";"
            cr.execute(query)
            return True
        else:
            #The attribute mapping is null
            return True
    
magerp_product_attribute_set()

class magerp_product_attribute_groups(magerp_osv.magerp_osv):
    _name = "magerp.product_attribute_groups"
    _description = "Attribute groups in Magento"
    _rec_name = 'attribute_group_name'
    _order = 'sort_order'
    _LIST_METHOD = 'ol_catalog_product_attribute_group.list'
    def set_get(self, cr, uid, ids, context=None):
        if not len(ids):
            return []
        reads = self.read(cr, uid, ids, ['attribute_set_id', 'instance'], context)
        res = []
        for record in reads:
            rid = self.pool.get('magerp.product_attribute_set').mage_to_oe(cr, uid, record['attribute_set_id'], record['instance'][0])
            if rid:
                res.append((record['id'], rid))
        return res
    
    def _get_set(self, cr, uid, ids, prop, unknow_none, context):
        res = self.set_get(cr, uid, ids, context)
        return dict(res) 
    
    _columns = {
        'magento_id':fields.integer('Group ID'),
        'attribute_set_id':fields.integer('Attribute Set ID'),
        'attribute_set':fields.function(_get_set, type="many2one", relation="magerp.product_attribute_set", method=True, string="Attribute Set"),
        'attribute_group_name':fields.char('Group Name', size=100),
        'sort_order':fields.integer('Sort Order'),
        'default_id':fields.integer('Default'),
        'instance':fields.many2one('external.referential', 'Magento Instance', readonly=True, store=True),
                }
magerp_product_attribute_groups()

class product_tierprice(osv.osv):
    _name = "product.tierprice"
    _description = "Implements magento tier pricing"
    
    _columns = {
        'web_scope':fields.selection([
                    ('all', 'All Websites'),
                    ('specific', 'Specific Website'),
                                  ], 'Scope'),
        'website_id':fields.many2one('external.shop.group', 'Website'),
        'group_scope':fields.selection([
                            ('1', 'All groups'),
                            ('0', 'Specific group')
                                       ]),
        'cust_group':fields.many2one('res.partner.category', 'Customer Group'),
        'website_price':fields.float('Website Price', digits=(10, 2),),
        'price':fields.float('Price', digits=(10, 2),),
        'price_qty':fields.float('Quantity Slab', digits=(10, 4), help="Slab & above eg.For 10 and above enter 10"),
        'product':fields.many2one('product.product', 'Product'),
        'instance':fields.many2one('external.referential', 'Magento Instance', readonly=True, store=True),
                }
    _mapping = {
        'cust_group':(False, int, """result=self.pool.get('res.partner.category').mage_to_oe(cr,uid,cust_group,instance)\nif result:\n\tresult=[('cust_group',result[0])]\nelse:\n\tresult=[('cust_group',False)]"""),
        'all_groups':(False, str, """if all_groups=='1':\n\tresult=[('group_scope','1')]\nelse:\n\tresult=[('group_scope','1')]"""),
        'website_price':('website_price', float),
        'price':('price', float),
        'website_id':(False, int, """result=self.pool.get('external.shop.group').mage_to_oe(cr,uid,website_id,instance)\nif result:\n\tresult=[('website_id',result[0])]\nelse:\n\tresult=[('website_id',False)]"""),
        'price_qty':('price_qty', float),
                }
product_tierprice()

class product_product(magerp_osv.magerp_osv):
    _inherit = "product.product"

    _columns = {
        'magento_id':fields.integer('Magento ID', readonly=True, store=True),
        'magento_sku':fields.char('Magento SKU', size=64),
        'exportable':fields.boolean('Exported to magento?'),
        'instance':fields.many2one('external.referential', 'Magento Instance', readonly=True, store=True),
        'created_at':fields.date('Created'), #created_at & updated_at in magento side, to allow filtering/search inside OpenERP!
        'updated_at':fields.date('Created'),
        'set':fields.many2one('magerp.product_attribute_set', 'Attribute Set'),
        'tier_price':fields.one2many('product.tierprice', 'product', 'Tier Price'),
        }
    _mapping = {
        'product_id':('magento_id', int)
                }
    _defaults = {
        'exportable':lambda * a:True
                 }

    def write(self, cr, uid, ids, vals, context={}):
        if vals.get('instance', False):
            instance = vals['instance']
            #Filter the keys to be changes
            if ids:
                if type(ids) == list and len(ids) == 1:
                    ids = ids[0]
                elif type(ids) == int or type(ids) == long:
                    ids = ids
                else:
                    return False
            tier_price = False
            if 'x_magerp_tier_price' in vals.keys(): 
                tier_price = vals.pop('x_magerp_tier_price')
            tp_obj = self.pool.get('product.tierprice')
            #Delete existing tier prices
            tier_price_ids = tp_obj.search(cr, uid, [('product', '=', ids)])
            if tier_price_ids:
                tp_obj.unlink(cr, uid, tier_price_ids)
            #Save the tier price
            if tier_price:
                self.create_tier_price(cr, uid, tier_price, instance, ids)
        stat = super(product_product, self).write(cr, uid, ids, vals, context)
        #Perform other operation
        return stat
    
    def create_tier_price(self, cr, uid, tier_price, instance, product_id):
        tp_obj = self.pool.get('product.tierprice')
        for each in eval(tier_price):
            tier_vals = {}
            cust_group = self.pool.get('res.partner.category').mage_to_oe(cr, uid, int(each['cust_group']), instance)
            if cust_group:
                tier_vals['cust_group'] = cust_group[0]
            else:
                tier_vals['cust_group'] = False
            tier_vals['website_price'] = float(each['website_price'])
            tier_vals['price'] = float(each['price'])
            tier_vals['price_qty'] = float(each['price_qty'])
            tier_vals['product'] = product_id
            tier_vals['instance'] = instance
            tier_vals['group_scope'] = each['all_groups']
            if each['website_id'] == '0':
                tier_vals['web_scope'] = 'all'
            else:
                tier_vals['web_scope'] = 'specific'
                tier_vals['website_id'] = self.pool.get('external.shop.group').mage_to_oe(cr, uid, int(each['website_id']), instance)
            tp_obj.create(cr, uid, tier_vals)
    
    def create(self, cr, uid, vals, context={}):
        tier_price = False
        if vals.get('instance', False):
            instance = vals['instance']
            #Filter keys to be changed
            if 'x_magerp_tier_price' in vals.keys(): 
                tier_price = vals.pop('x_magerp_tier_price')
        print vals
        crid = super(product_product, self).create(cr, uid, vals, context)
        #Save the tier price
        if tier_price:
            self.create_tier_price(cr, uid, tier_price, instance, crid)
        #Perform other operations
        return crid
    
    #TODO move part of this to declarative mapping CSV template
    def oe_record_to_mage_data(self, cr, uid, product, context={}):
        pricelist_obj = self.pool.get('product.pricelist')
        pl_default_id = pricelist_obj.search(cr, uid, [('type', '=', 'sale')]) #TODO pricelist_obj.search(cr, uid, [('magento_default', '=', True)])
        product_data = { #TODO refactor that using existing mappings? Add extra attributes?
                'name': product.name,
                'price' : pricelist_obj.price_get(cr, uid, pl_default_id, product.id, 1.0)[pl_default_id[0]],
                'weight': (product.weight_net or 0),
                'category_ids': [categ.category_id for categ in product.categ_ids],
                'description' : (product.description or _("description")),
                'short_description' : (product.description_sale or _("short description")),
                'websites':['base'],
                'tax_class_id': 2, #product.magento_tax_class_id or 2 ? TODO mapp taxes!
                'status': product.active and 1 or 2,
                'meta_title': product.name,
                'meta_keyword': product.name,
                'meta_description': product.description_sale and product.description_sale[:255],
        }
        
        #now mapp the attributes from created after the Magento EAV attributes model:
        ir_model_id = self.pool.get('ir.model').search(cr, uid, [('model', '=', 'product.product')])[0]
        ir_model = self.pool.get('ir.model').browse(cr, uid, ir_model_id)
        ir_model_field_ids = self.pool.get('ir.model.fields').search(cr, uid, [('model_id', '=', ir_model_id), ('ttype', '=', 'char')])
        ir_model_field_ids += self.pool.get('ir.model.fields').search(cr, uid, [('model_id', '=', ir_model_id), ('ttype', '=', 'date')])
        ir_model_field_ids += self.pool.get('ir.model.fields').search(cr, uid, [('model_id', '=', ir_model_id), ('ttype', '=', 'int')])
        ir_model_field_ids += self.pool.get('ir.model.fields').search(cr, uid, [('model_id', '=', ir_model_id), ('ttype', '=', 'float')])
        ir_model_field_ids += self.pool.get('ir.model.fields').search(cr, uid, [('model_id', '=', ir_model_id), ('ttype', '=', 'text')])
        field_names = [str(field.name).startswith('x_') and field.name for field in self.pool.get('ir.model.fields').browse(cr, uid, ir_model_field_ids)]
        attributes = self.read(cr, uid, product.id, field_names, {})
        del(attributes['id'])
        #TODO: also deal with many2one option fields!
        product_data.update(attributes)
        return product_data

    def product_to_sku(self, cr, uid, product):
        if product.magento_sku:
            sku = product.magento_sku
        else:
            code = product.code or 'mag'
            same_codes = self.search(cr, uid, [('magento_sku', '=', code)])
            if same_codes and len(same_codes) > 0:
                sku = code + "_" + str(product.id)
            else:
                sku = code
        return sku

    def ext_export(self, cr, uid, ids, external_referential_ids=[], defaults={}, context={}):
        """overriden to set the default_set_id in context and avoid extra request for each product upload"""
        conn = context.get('conn_obj', False)
        sets = conn.call('product_attribute_set.list')
        default_set_id = 1
        for set in sets:
            if set['name'] == 'Default':
                default_set_id = set['set_id']
                break
        context['default_set_id'] = default_set_id
        return super(magerp_osv.magerp_osv, self).ext_export(cr, uid, ids, external_referential_ids, defaults, context)

    #TODO mapp all attributes
    def extdata_from_oevals(self, cr, uid, external_referential_id, data_record, mapping_lines, defaults, context):
        product = self.browse(cr, uid, data_record['id'])
        sku = self.product_to_sku(cr, uid, product)
        
        if product.set and product.set.attribute_set_id:
            attr_set_id = product.set.attribute_set_id.id
        else:
            attr_set_id = context.get('default_set_id', False)

        product_data = self.oe_record_to_mage_data(cr, uid, product, context)
        return product_data
    
    def _export_inventory(self, cr, uid, product, stock_id, logger, ctx):
        if product.magento_sku and product.type != 'service':
            virtual_available = self.read(cr, uid, product.id, ['virtual_available'], {'location': stock_id})['virtual_available']
            ctx['conn_obj'].call('product_stock.update', [product.magento_sku, {'qty': virtual_available, 'is_in_stock': 1}])
            logger.notifyChannel('ext synchro', netsvc.LOG_INFO, "Successfully updated stock level at %s for product with SKU %s " %(virtual_available, product.magento_sku))
    
    def ext_create(self, cr, uid, data, conn, method, oe_id, ctx):        
        product = self.browse(cr, uid, oe_id)
        sku = self.product_to_sku(cr, uid, product)
        virtual_available = product.virtual_available
        attr_set_id = product.set and product.set.attribute_set_id or ctx.get('default_set_id', 1) #TODO check
        product_type = 'simple'

        res = super(magerp_osv.magerp_osv, self).ext_create(cr, uid, [product_type, attr_set_id, sku, data], conn, method, oe_id, ctx)
        self.write(cr, uid, oe_id, {'magento_sku': sku})
        stock_id = self.pool.get('sale.shop').browse(cr, uid, ctx['shop_id']).warehouse_id.lot_stock_id.id
        logger = netsvc.Logger()
        self._export_inventory(cr, uid, product, stock_id, logger, ctx)
        return res
    
    def ext_update(self, cr, uid, data, conn, method, oe_id, external_id, ir_model_data_id, create_method, ctx):
        product = self.browse(cr, uid, oe_id)
        sku = self.product_to_sku(cr, uid, product)
        virtual_available = product.virtual_available
        attr_set_id = product.set and product.set.attribute_set_id or ctx.get('default_set_id', 1) #TODO check

        res = super(magerp_osv.magerp_osv, self).ext_update(cr, uid, data, conn, method, oe_id, sku, ir_model_data_id, create_method, ctx)
        stock_id = self.pool.get('sale.shop').browse(cr, uid, ctx['shop_id']).warehouse_id.lot_stock_id.id
        logger = netsvc.Logger()
        self._export_inventory(cr, uid, product, stock_id, logger, ctx)
        return res
    
    def export_inventory(self, cr, uid, ids, shop, ctx):
        logger = netsvc.Logger()
        stock_id = self.pool.get('sale.shop').browse(cr, uid, ctx['shop_id']).warehouse_id.lot_stock_id.id
        for product in self.browse(cr, uid, ids):
            self._export_inventory(cr, uid, product, stock_id, logger, ctx)


product_product()
