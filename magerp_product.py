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
    
    _columns = {
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
                    ('None', 'Use Config Settings'),
                    ('position', 'Best Value'),
                    ('name', 'Name'),
                    ('price', 'Price')
                    ], 'Available Product Listing (Sort By)', required=True),
        'default_sort_by': fields.selection([
                    ('None', 'Use Config Settings'),
                    ('position', 'Best Value'),
                    ('name', 'Name'),
                    ('price', 'Price')
                    ], 'Default Product Listing Sort (Sort By)', required=True),
        'magerp_stamp':fields.datetime('Magento stamp')
        }
    _defaults = {
        'display_mode':lambda * a:'PRODUCTS',
        'available_sort_by':lambda * a:'None',
        'default_sort_by':lambda * a:'None',
        'level':lambda * a:1
                 }
    
    _mapping = {
        'category_id':('magento_id', int),
        'level':(False, int, """result=[('sequence',level),('level',level)]"""),
        'parent_id':('magento_parent_id', int),
        'is_active':('is_active', bool),
        'description':('description', str),
        'meta_title':('meta_title', str),
        'meta_keywords':('meta_keywords', str),
        'meta_description':('meta_description', str),
        'url_key':('url_key', str),
        'is_anchor':('is_anchor', bool),
        'available_sort_by':('available_sort_by', str),
        'default_sort_by':('default_sort_by', str),
        'name':('name', str),
        'updated_at':('updated_at', str)
                
                }
    IMPORT_KEYS = [
                   ('category_id', 'magento_id', 'NONE2FALSE'),
                   ('level', 'sequence', 'NONE2FALSE'),
                   ('level', '', 'NONE2FALSE'),
                   ('parent_id', 'magento_parent_id', 'NONE2FALSE'),
                   ('is_active', '', 'NONE2FALSE'),
                   ('description', '', 'NONE2FALSE'),
                   ('image', '', 'NONE2FALSE'),
                   ('image', 'image_name', 'NONE2FALSE'),
                   ('meta_title', '', 'NONE2FALSE'),
                   ('meta_keywords', '', 'NONE2FALSE'),
                   ('meta_description', '', 'NONE2FALSE'),
                   ('url_key', '', 'NONE2FALSE'),
                   ('display_mode', '', 'NONE2STR', 'PRODUCTS'),
                   ('is_anchor', '', 'NONE2FALSE'),
                   ('available_sort_by', '', 'NONE2STR', 'None'),
                   ('default_sort_by', '', 'NONE2STR', 'None'),
                   ('name', '', 'NONE2FALSE'),
                   ('updated_at', 'magerp_stamp', 'NONE2FALSE')
                   ]
    
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
        imp_vals = self.cast_string(conn.call('category.info', [category_id]))
        self.ext_import(cr, uid, [imp_vals], external_referential_id, defaults={}, context={})
        #Replace code by new method
        """vals = {}
        imp_keys = self.IMPORT_KEYS
        for eachkey in imp_keys:
            #Check if there is any key renames
            if imp_vals[eachkey[0]] == None:
                if eachkey[2] == 'NONE2FALSE':
                    imp_val = False
                elif eachkey[2] == 'NONE2STR':
                    imp_val = eachkey[3] or 'None'
            else:
                imp_val = imp_vals[eachkey[0]]
                
            if eachkey[1] == '':
                vals[eachkey[0]] = imp_val
            else:
                vals[eachkey[1]] = imp_val       
        
        if vals['image']:
            #IMage exists
            #vals['image'] = conn.fetch_image("media/catalog/category/" + vals['image_name'])
            try:
                vals['image'] = conn.call('ol_catalog_category_media.info', [int(imp_vals['category_id'])])
            except Exception, e:
                pass
            if vals['image']:
                vals['image'] = base64.encodestring(base64.urlsafe_b64decode(vals['image'][0]['image_data']))
#                flob = open('/home/sharoon/Desktop/' + vals['image_name'], 'wb')
#                flob.write(base64.decodestring(vals['image']))
#                flob.close()
        if vals['available_sort_by'] == '':
            vals['available_sort_by'] = 'None'
        vals['parent_id'] = self.mage_to_oe(cr, uid, imp_vals['parent_id'], id)
        if vals['parent_id'] == None:
            vals['parent_id'] = False
        if vals['parent_id']:
            vals['parent_id'] = vals['parent_id'][0]
        vals['instance'] = id
        vals['sequence'] = id
        vals['exportable'] = True
        vals['updated'] = False
        #Check if already exists?
        pcat_ids = self.search(cr, uid, [('magento_id', '=', category_id), ('instance', '=', id)])
        if not pcat_ids:
            #Category is not there
            #print vals
            return self.create(cr, uid, vals)
        else:
            #Category Exists,update it if its newer
            existing_rec_date = self.read(cr, uid, pcat_ids[0], ['magerp_stamp'])['magerp_stamp']
            inc_rec_date = datetime.datetime.fromtimestamp(time.mktime(time.strptime(imp_vals['updated_at'], '%Y-%m-%d %H:%M:%S')))
            existing_rec_date = datetime.datetime.fromtimestamp(time.mktime(time.strptime(existing_rec_date, '%Y-%m-%d %H:%M:%S')))
            if inc_rec_date > existing_rec_date:
                #Existing data is old
                return self.write(cr, uid, pcat_ids, vals)
            elif inc_rec_date < existing_rec_date:
                #Existing data is new, export this
                self.export_2_mage(cr, uid, pcat_ids, conn)"""
                
    def export_2_mage(self, cr, uid, ids, conn, ctx={}):
        if conn:
            print "Connection exists"
        else:
            print "create connection"
        records = self.read(cr, uid, ids, [])
        for record in records:
            if record['exportable']:
                vals = {}
                imp_keys = self.IMPORT_KEYS
                for eachkey in imp_keys:
                    if record[eachkey[1] or eachkey[0]] in [None, False, 'None']:
                        value = 'None'
                    else:
                        value = record[eachkey[1] or eachkey[0]]
                    vals[eachkey[0]] = value
                if record['image']:
                    img = base64.decodestring(record['image'])
                    #img = "hello"
                    img_bin_enc = base64.encodestring(img) 
                    result = conn.call('ol_catalog_category_media.create', [record['image_name'], img_bin_enc])
                    if result == img:
                        print "you know how to decode"
                    #TODO:upload image now
                if vals['available_sort_by'] == 'None':
                    vals['available_sort_by'] = ''
                    #all operations are assumed to be complete before this line
                    #remove category_id from keys
                    vals.pop('magento_id')
                if not record['magento_id']:
                    #Record was never created on magento side, so create new
                    conn.call('catalog_category.create', [vals])
                else:
                    #Record was created, now update it
                    if conn.call('catalog_category.update', [record['magento_id'], vals]):
                        cross_check = conn.call('catalog_category.info', [record['magento_id']])
                        self.write(cr, uid, record['id'], {
                                    'updated':False,
                                    'magerp_stamp':cross_check['updated_at']
                                                        })
                    
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
        'map_in_openerp':fields.boolean('Map in Open ERP?'),
        'mapping_field_name':fields.char('Field name', size=100),
        'mapping_type_cast':fields.char('Type cast', size=20),
        'mapping_script':fields.text('Python Script', help="Write python script here"),
        }
    #mapping magentofield:(openerpfield,typecast,)
    #have an entry for each mapped field
    _mapping = {
        'code':('attribute_code', str),
        'attribute_id':('magento_id', int),
        #'set_id':('set_id',int), #Depreciated from mapping as its an m2m relation
        'frontend_input':('frontend_input', str),
        'frontend_class':('frontend_class', str),
        'backend_model':('backend_model', str),
        'backend_type':('backend_type', str),
        'frontend_label':('frontend_label', str),
        'is_visible_in_advanced_search':('is_visible_in_advanced_search', bool),
        'is_global':('is_global', bool),
        'is_filterable':('is_filterable', bool),
        'is_comparable':('is_comparable', bool),
        'is_visible':('is_visible', bool),
        'is_searchable':('is_searchable', bool),
        'is_user_defined':('is_user_defined', bool),
        'is_configurable':('is_configurable', bool),
        'is_visible_on_front':('is_visible_on_front', bool),
        'is_used_for_price_rules':('is_used_for_price_rules', bool),
        'is_unique':('is_unique', bool),
        'is_required':('is_required', bool),
        'position':('position', int),
        'group_id': ('group_id', int),
        #'apply_to': ('apply_to',str),
        'default_value': ('default_value', str),
        'note':('default_value', str),
        'entity_type_id':('entity_type_id', int),
        
                }
    _known_attributes = {
        'product_id':('product_id'),
        'name':('name', 'str', False),
        'description':('description', 'str'),
        'short_description':('description_sale', 'str'),
        'sku':('default_code', 'str'),
        'weight':('weight_net', 'float'),
        #Categ id is many2one, but do it for m2m
        'category_ids':(False, 'False', """if category_ids:\n\tresult=self.pool.get('product.category').mage_to_oe(cr,uid,category_ids[0],instance)\n\tif result:\n\t\tresult=[('categ_id',result[0])]\nelse:\n\tresult=self.pool.get('product.category').search(cr,uid,[('instance','=',instance)])\n\tif result:\n\t\tresult=[('categ_id',result[0])]"""),
        'created_at':('created_at', 'str'),
        'updated_at':('updated_at', 'str'),
        'price':('list_price', 'float'),
        'cost':('standard_price', 'float'),
        'set':(False, 'int', """if set:\n\tresult=self.pool.get('magerp.product_attribute_set').mage_to_oe(cr,uid,set,instance)\n\tif result:\n\t\tresult=[('set',result[0])]\n\telse:\n\t\tresult=[('set',False)]\nelse:\n\tresult=[('set',False)]"""),
                         }
    _ignored_attributes = [

                           ]
    def create(self, cr, uid, vals, context={}):
        field_name = "x_magerp_" + vals['attribute_code']
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
        if vals['attribute_code'] in self._known_attributes.keys():
            vals['map_in_openerp'] = True
            vals['mapping_field_name'] = self._known_attributes[vals['attribute_code']][0]
            vals['mapping_type_cast'] = self._known_attributes[vals['attribute_code']][1]
            try:
                vals['mapping_script'] = self._known_attributes[vals['attribute_code']][2]
            except:
                vals['mapping_script'] = False
        elif vals['attribute_code'] in self._ignored_attributes:
            vals['map_in_openerp'] = False
        else:
            vals['map_in_openerp'] = True
            if 'frontend_input' in vals.keys() and vals['frontend_input'] == 'date':
                vals['mapping_field_name'] = False
                vals['mapping_type_cast'] = 'str'
                vals['mapping_script'] = "if " + vals['attribute_code'] + "=='None':\n\tresult=[(" + field_name + ",False)]\nelse:\n\tresult=[(" + field_name + "," + vals['attribute_code'] + ")]"
            elif 'frontend_input' in vals.keys() and  vals['frontend_input'] == 'select':
                vals['mapping_field_name'] = False
                vals['mapping_type_cast'] = 'str'
                vals['mapping_script'] = "if " + vals['attribute_code'] + ":\n\t\result=self.pool.get('magerp.product_attribute_options').get_option_id(cr,uid,'" + vals['attribute_code'] + "'," + vals['attribute_code'] + ",instance)\n\tif result:\n\t\tresult=[('" + vals['attribute_code'] + "',result)]"
            else:
                vals['mapping_field_name'] = field_name
                vals['mapping_type_cast'] = type_casts[vals.get('frontend_input',False)]
            
        crid = super(magerp_product_attributes, self).create(cr, uid, vals, context)
        
        if crid:
            #Fetch Options
            if 'frontend_input' in vals.keys() and vals['frontend_input'] in ['select']:
                core_conn = self.pool.get('external.referential').connect(cr, uid, [vals['instance']])
                self.pool.get('magerp.product_attribute_options').mage_import(cr, uid, [vals['magento_id']], core_conn, vals['instance'], debug=False, defaults={'attribute_id':crid})
            #Manage fields
            if vals['attribute_code'] and vals['map_in_openerp']:
                #Code for dynamically generating field name and attaching to this
                model_id = self.pool.get('ir.model').search(cr, uid, [('model', '=', 'product.product')])
                if model_id and len(model_id) == 1:
                    model_id = model_id[0]
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
                    
                    #Check if field already exists
                    field_ids = self.pool.get('ir.model.fields').search(cr, uid, [('name', '=', field_name), ('model_id', '=', model_id)])
                    if not field_ids:
                        #The field is not there create it
                        field_vals = {
                            'name':field_name,
                            'model_id':model_id,
                            'model':'product.product',
                            'field_description':vals.get('frontend_label', False) or vals['attribute_code'],
                            'ttype':type_conversion[vals.get('frontend_input',False)],
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
        return crid
    

magerp_product_attributes()

class magerp_product_attribute_options(magerp_osv.magerp_osv):
    _name = "magerp.product_attribute_options"
    _description = "Options  of selected attributes"
    _MAGE_FIELD = False
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
    _mapping = {
        'value':('value', str,),
        'label':('label', str)
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
    _mapping = {
        'attribute_set_id':('magento_id', int),
        'sort_order':('sort_order', int),
        'attribute_set_name':('attribute_set_name', str)
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
    _mapping = {
        'attribute_group_id':('magento_id', int),
        'attribute_set_id':('attribute_set_id', int),
        'attribute_group_name':('attribute_group_name', str),
        'sort_order':('sort_order', int),
        'default_id':('default_id', int)
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
    _LIST_METHOD = "catalog_product.list"
    _INFO_METHOD = "catalog_product.info"
    _CREATE_METHOD = "product.create"
    _UPDATE_METHOD = "product.update"
    #Just implement a simple product synch
    _columns = {
        'magento_id':fields.integer('Magento ID', readonly=True, store=True),
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
        'exportable':lambda *a:True
                 }
    def mage_import(self, cr, uid, ids_or_filter, conn, instance, debug=False, defaults={}, *attrs):
        #Build the mapping dictionary dynamically from attributes
        inst_attrs = self.pool.get('magerp.product_attributes').search(cr, uid, [('instance', '=', instance), ('map_in_openerp', '=', '1')])
        inst_attrs_reads = self.pool.get('magerp.product_attributes').read(cr, uid, inst_attrs, ['attribute_code', 'mapping_field_name', 'mapping_type_cast', 'mapping_script'])
        for each in inst_attrs_reads:
            if type(each['mapping_type_cast']) == unicode:
                self._mapping[each['attribute_code']] = (each['mapping_field_name'], eval(each['mapping_type_cast']), each['mapping_script'])
            else:
                self._mapping[each['attribute_code']] = (each['mapping_field_name'], each['mapping_type_cast'], each['mapping_script'])
        #If mapping dictionary exists then synchronise
        if self._mapping:
            list_prods = conn.call(self._LIST_METHOD, ids_or_filter)
            result = []
            for each in list_prods:
                each_product_info = conn.call(self._INFO_METHOD, [each['product_id']])
                result.append(each_product_info)
            #result contains detailed info of all products
            if attrs:
                self.sync_import(cr, uid, result, instance, debug, defaults, attrs)
            else:
                self.sync_import(cr, uid, result, instance, debug, defaults)
        else:
            raise osv.except_osv(_('Undefined Mapping !'), _("Mapping dictionary is not present in the object!\nMake sure attributes are synchronised first"))

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
        crid = super(product_product, self).create(cr, uid, vals, context)
        #Save the tier price
        if tier_price:
            self.create_tier_price(cr, uid, tier_price, instance, crid)
        #Perform other operations
        return crid
    
    def oe_record_to_mage_data(self, cr, uid, product, conn, instance, context={}):
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
        return product_data

    
    def oe_record_to_mage_create(self, cr, uid, ids, conn, instance, context={}):
        #default attribute set:
        sets = conn.call('product_attribute_set.list')
        default_set_id = 1
        for set in sets:
            if set['name'] == 'Default':
                default_set_id = set['set_id']
                break
        mage_records = []
        for product in self.browse(cr, uid, ids):
            sku = (product.code or "mag") + "_" + str(product.id)
            
            if product.set and product.set.attribute_set_id:
                attr_set_id = product.set.attribute_set_id.id
            else:
                attr_set_id = default_set_id

            product_data = self.oe_record_to_mage_data(cr, uid, product, conn, instance, context)
            mage_record = (product.id, ['simple', attr_set_id, sku, product_data])
            mage_records.append(mage_record)
        return mage_records
    
    def oe_record_to_mage_update(self, cr, uid, ids, conn, instance, context={}):
        mage_records = []
        for product in self.browse(cr, uid, ids):
            product_data = self.oe_record_to_mage_data(cr, uid, product, conn, instance, context)
            if product.x_magerp_sku:
                sku = product.x_magerp_sku
            else:
                sku = (product.code or "mag") + "_" + str(product.id)
            mage_record = (product.id, [sku, product_data])
            mage_records.append(mage_record)
        return mage_records

product_product()
