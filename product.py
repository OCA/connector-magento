# -*- encoding: utf-8 -*-
#########################################################################
#This module intergrates Open ERP with the magento core                 #
#Core settings are stored here                                          #
#########################################################################
#                                                                       #
# Copyright (C) 2009  Sharoon Thomas, Raphaël Valyi                     #
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
import datetime
import base64
import time
import magerp_osv
from tools.translate import _
import netsvc


class product_category(magerp_osv.magerp_osv):
    _inherit = "product.category"
    
#    def name_get(self, cr, uid, ids, context=None):
#        if not len(ids):
#            return []
#        reads = self.read(cr, uid, ids, ['name', 'parent_id', 'instance'], context)
#        res = []
#        for record in reads:
#            name = record['name']
#            if record['parent_id']:
#                name = record['parent_id'][1] + ' / ' + name
#            if record['instance'] and not record['parent_id']:
#                name = "[" + record['instance'][1] + "] " + name 
#            res.append((record['id'], name))
#        return res

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
        #*************** Magento Fields ********************
        #==== General Information ====
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
    
    def _get_group(self, cr, uid, ids, prop, unknow_none, context):
        res = {}
        for attribute in self.browse(cr, uid, ids, context):
            res[attribute.id] = self.pool.get('magerp.product_attribute_groups').extid_to_oeid(cr, uid, attribute.group_id, attribute.referential_id.id)
        return res
    
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
                                           ('multiselect', 'Multi-Selection'),
                                           ('date', 'Date'),
                                           ('price', 'Price'),
                                           ('media_image', 'Media Image'),
                                           ('gallery', 'Gallery'),
                                           ('weee', 'Fixed Product Tax')
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
        'referential_id':fields.many2one('external.referential', 'Magento Instance', readonly=True),
        #These parameters are for automatic management
        'field_name':fields.char('Open ERP Field name', size=100),
        'attribute_set_info':fields.text('Attribute Set Information')
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
        if 'attribute_set_info' in vals.keys():
            attr_set_info = eval(vals.get('attribute_set_info',{}))
            for each_key in attr_set_info.keys():
                vals['group_id']=attr_set_info[each_key].get('group_id',False)
                
        crid = super(magerp_product_attributes, self).create(cr, uid, vals, context)
        if not vals['attribute_code'] in self._no_create_list:
            #If the field has to be created
            if crid:
                #Fetch Options
                if 'frontend_input' in vals.keys() and vals['frontend_input'] in ['select']:
                    core_imp_conn = self.pool.get('external.referential').connect(cr, uid, [vals['referential_id']])
                    options_data = core_imp_conn.call('ol_catalog_product_attribute.options',[vals['magento_id']])
                    if options_data:
                        self.pool.get('magerp.product_attribute_options').data_to_save(cr,uid,options_data,context={'attribute_id':crid,'referential_id':vals['referential_id']})
                    #self.pool.get('magerp.product_attribute_options').mage_import_base(cr, uid, core_imp_conn, inst.id, defaults={'attribute_id':crid,'ids_or_filter':[vals['magento_id']]})
                #Manage fields
                if vals['attribute_code'] and vals.get('frontend_input', False):
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
                            'multiselect':'char',
                            'weee':'char',
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
                            'multiselect':'str',
                            'weee':'str',
                            False:'str'
                            }
                    if model_id and len(model_id) == 1:
                        model_id = model_id[0]
                        #Check if field already exists
                        referential_id = context.get('referential_id',False)
                        field_ids = self.pool.get('ir.model.fields').search(cr, uid, [('name', '=', field_name), ('model_id', '=', model_id)])
                        field_vals = {
                                        'name':field_name,
                                        'model_id':model_id,
                                        'model':'product.product',
                                        'field_description':vals.get('frontend_label', False) or vals['attribute_code'],
                                        'ttype':type_conversion[vals.get('frontend_input', False)],
                                      }
                        if not field_ids:
                            #The field is not there create it
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
                            existing_line = self.pool.get('external.mapping.line').search(cr, uid, [('external_field', '=', vals['attribute_code']), ('mapping_id', '=', mapping_id[0])])
                            if not existing_line or len(existing_line) == 0:
                                field_id = field_ids[0]
                                mapping_line = {
                                                    'external_field': vals['attribute_code'],
                                                    'mapping_id': mapping_id[0],
                                                    'type': 'in_out',
                                                    'external_type':type_casts[vals.get('frontend_input', False)],
                                                }
                                mapping_line['field_id'] = field_id,
                                if field_vals['ttype'] in ['char','text','date','float','weee']:
                                    mapping_line['in_function'] = "result =[('" + field_name + "',ifield)]"
                                    mapping_line['out_function'] = "result=[('%s',record['%s'])]" % (vals['attribute_code'], field_name)
                                elif field_vals['ttype'] in ['many2one']:
                                    mapping_line['in_function'] = "if ifield:\n\toption_id = self.pool.get('magerp.product_attribute_options').search(cr,uid,[('attribute_id','=',%s),('value','=',ifield)])\n\tif option_id:\n\t\t\tresult = [('"  % crid
                                    mapping_line['in_function'] += field_name + "',option_id[0])]"
                                    mapping_line['out_function'] = "if record['%s']:\n\toption=self.pool.get('magerp.product_attribute_options').browse(cr, uid, record['%s'][0])\n\tif option:\n\t\tresult=[('%s',option.value)]" % (field_name, field_name, vals['attribute_code'])
                                elif field_vals['ttype'] in ['multiselect']:
                                    mapping_line['in_function'] = "result=[('%s',str(ifield))]" % field_name
                                    mapping_line['out_function'] = "result= record['%s'] and [('%s', eval(record['%s']))] or []" % (field_name, vals['attribute_code'], field_name)
                                elif field_vals['ttype'] in ['binary']:
                                    print "Binary mapping not done yet :("
                                self.pool.get('external.mapping.line').create(cr,uid,mapping_line)
        return crid

magerp_product_attributes()
"""Dont remove the code, we might need it --sharoon
class magerp_product_attributes_set_info(osv.osv):
    _name="magerp.product_attributes.set_info"
    _description = "Attribute Set information for each attribute"
    _columns = {
        'referential_id':fields.many2one('external.referential', 'Magento Instance', readonly=True),
        'attribute_set_id':
        'sort':fields.integer('sort')
        'group_sort':fields.integer('group_sort')
        'group_id':
                }
magerp_product_attributes_set_info()"""
class magerp_product_attribute_options(magerp_osv.magerp_osv):
    _name = "magerp.product_attribute_options"
    _description = "Options  of selected attributes"
    _rec_name = "label"
    
    _columns = {
                'attribute_id':fields.many2one('magerp.product_attributes', 'Attribute'),
                'attribute_name':fields.related('attribute_id', 'attribute_code', type='char', string='Attribute Code',),
                'value':fields.char('Value', size=200),
                'ipcast':fields.char('Type cast', size=50),
                'label':fields.char('Label', size=100),
                'referential_id':fields.many2one('external.referential', 'Magento Instance', readonly=True),
                }
    def data_to_save(self,cr,uid,vals_list,context={}):
        """This method will take data from vals and use context to create record"""
        for vals in vals_list:
            if vals.get('value',False) and vals.get('label',False):
                #Fixme: What to do when magento offers emty options which open erp doesnt?
                #Such cases dictionary is: {'value':'','label':''}
                self.create(cr,uid,
                            {
                        'attribute_id':context.get('attribute_id',False),
                        'value':vals.get('value',False),
                        'label':vals.get('label',False),
                        'referential_id':context.get('referential_id',False),
                             }
                            ) 
    def get_option_id(self, cr, uid, attr_name, value, instance):
        attr_id = self.search(cr, uid, [('attribute_name', '=', attr_name), ('value', '=', value), ('referential_id', '=', instance)])
        if attr_id:
            return attr_id[0]
        else:
            return False
magerp_product_attribute_options()

class magerp_product_attribute_set(magerp_osv.magerp_osv):
    _name = "magerp.product_attribute_set"
    _description = "Attribute sets in products"
    _rec_name = 'attribute_set_name'
    
    _columns = {
        'sort_order':fields.integer('Sort Order'),
        'attribute_set_name':fields.char('Set Name', size=100),
        'attributes':fields.many2many('magerp.product_attributes', 'magerp_attrset_attr_rel', 'set_id', 'attr_id', 'Attributes'),
        'referential_id':fields.many2one('external.referential', 'Magento Instance', readonly=True),
        'magento_id':fields.integer('Magento ID'),
        }
    
    def create_product_menu(self, cr, uid, ids, vals, context):
        data_ids = self.pool.get('ir.model.data').search(cr, uid, [('name', '=', 'menu_products'), ('module', '=', 'product')])
        if data_ids:
            product_menu_id = self.pool.get('ir.model.data').read(cr, uid, data_ids[0], ['res_id'])['res_id']
        if type(ids) != list:
            ids = [ids]

        for attribute_set in self.browse(cr, uid, ids, context):
            menu_vals = {
                            'name': attribute_set.attribute_set_name,
                            'parent_id': product_menu_id,
                            'icon': 'STOCK_JUSTIFY_FILL'
            }
            
            action_vals = {
                            'name': attribute_set.attribute_set_name,
                            'view_type':'form',
                            'domain':attribute_set.attribute_set_name != 'Default' and "[('set', '=', %s)]" % attribute_set.id or "",
                            'context': "{'set':%s}" % attribute_set.id,
                            'res_model': 'product.product'
            }
            
            existing_menu_id = self.pool.get('ir.ui.menu').search(cr, uid, [('name', '=', attribute_set.attribute_set_name)])
            if len(existing_menu_id) > 0:
                action_ref = self.pool.get('ir.ui.menu').browse(cr, uid, existing_menu_id[0]).action
                action_id = False
                if action_ref:
                    action_id = int(action_ref.split(',')[1])
                    self.pool.get('ir.actions.act_window').write(cr, uid, action_id, action_vals, context)
                else:
                    action_id = self.pool.get('ir.actions.act_window').create(cr, uid, action_vals, context)
                menu_vals['action'] = 'ir.actions.act_window,'+str(action_id)
                self.pool.get('ir.ui.menu').write(cr, uid, existing_menu_id[0], menu_vals, context)
            else:
                action_id = self.pool.get('ir.actions.act_window').create(cr, uid, action_vals, context)
                menu_vals['action'] = 'ir.actions.act_window,'+str(action_id)
                self.pool.get('ir.ui.menu').create(cr, uid, menu_vals, context)
    
    def write(self, cr, uid, ids, vals, context={}):
        res = super(magerp_product_attribute_set, self).write(cr, uid, ids, vals, context)
        self.create_product_menu(cr, uid, ids, vals, context)
        return res
    
    def create(self, cr, uid, vals, context={}):
         id = super(magerp_product_attribute_set, self).create(cr, uid, vals, context)
         self.create_product_menu(cr, uid, id, vals, context)
         return id

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
    _order = "sort_order"
    def _get_set(self, cr, uid, ids, prop, unknow_none, context):
        res = {}
        for attribute_group in self.browse(cr, uid, ids, context):
            res[attribute_group.id] = self.pool.get('magerp.product_attribute_set').extid_to_oeid(cr, uid, attribute_group.attribute_set_id, attribute_group.referential_id.id)
        return res
    
    _columns = {
                'attribute_set_id':fields.integer('Attribute Set ID'),
                'attribute_set':fields.function(_get_set, type="many2one", relation="magerp.product_attribute_set", method=True, string="Attribute Set"),
                'attribute_group_name':fields.char('Group Name', size=100),
                'sort_order':fields.integer('Sort Order'),
                'default_id':fields.integer('Default'),
                'referential_id':fields.many2one('external.referential', 'Magento Instance', readonly=True),
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
        'referential_id':fields.many2one('external.referential', 'Magento Instance', readonly=True),
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
        'magento_sku':fields.char('Magento SKU', size=64),
        'exportable':fields.boolean('Exported to Magento?'),
        'created_at':fields.date('Created'), #created_at & updated_at in magento side, to allow filtering/search inside OpenERP!
        'updated_at':fields.date('Created'),
        'set':fields.many2one('magerp.product_attribute_set', 'Attribute Set'),
        'tier_price':fields.one2many('product.tierprice', 'product', 'Tier Price'),
        }

    _defaults = {
        'exportable':lambda * a:True
                 }

    def write(self, cr, uid, ids, vals, context={}):
        if vals.get('referential_id', False):
            instance = vals['referential_id']
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
            tier_vals['referential_id'] = instance
            tier_vals['group_scope'] = each['all_groups']
            if each['website_id'] == '0':
                tier_vals['web_scope'] = 'all'
            else:
                tier_vals['web_scope'] = 'specific'
                tier_vals['website_id'] = self.pool.get('external.shop.group').mage_to_oe(cr, uid, int(each['website_id']), instance)
            tp_obj.create(cr, uid, tier_vals)
    
    def create(self, cr, uid, vals, context={}):
        tier_price = False
        if vals.get('referential_id', False):
            instance = vals['referential_id']
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


    def redefine_prod_view(self,cr,uid, field_names, attribute_set_id):
        #This function will rebuild the view for product from instances, attribute groups etc
        #Get all objects needed
        #inst_obj = self.pool.get('external.referential')
        attr_set_obj = self.pool.get('magerp.product_attribute_set')
        attr_group_obj = self.pool.get('magerp.product_attribute_groups')
        attr_obj = self.pool.get('magerp.product_attributes')
        xml = u"<notebook colspan='4'>\n"
        attr_grp_ids = attr_group_obj.search(cr,uid,[])
        attr_groups = attr_group_obj.browse(cr,uid,attr_grp_ids)
        
        attr_set = attr_set_obj.browse(cr, uid, attribute_set_id)
        
        cr.execute("select attr_id, group_id, attribute_code, frontend_input, frontend_label, is_required, apply_to  from magerp_attrset_attr_rel left join magerp_product_attributes on magerp_product_attributes.id = attr_id where magerp_attrset_attr_rel.set_id=%s" % attribute_set_id)
        results = cr.fetchall()
        result = results.pop()
        while len(results) > 0:
            mag_group_id = result[1]
            oerp_group_id = attr_group_obj.extid_to_oeid(cr, uid, mag_group_id, attr_set.referential_id.id)
            group_name = attr_group_obj.read(cr, uid, oerp_group_id, ['attribute_group_name'])['attribute_group_name']
            
            #Create a page for the attribute group
            xml+="<page string='" + group_name + "'>\n<group colspan='4' col='4'>"
            while len(results) > 0:
                if result[1] != mag_group_id:
                    break
                #TODO understand why we need to do "x_magerp_" +  each_attribute.attribute_code in field_names or fix it
                if "x_magerp_" +  result[2] in field_names:
                    if not result[2] in attr_obj._no_create_list:
                        if result[3] in ['textarea']:
                            xml+="<newline/><separator colspan='4' string='%s'/>" % (result[4],)
                        xml+="<field name='x_magerp_" +  result[2] + "'"
                        if result[5] and (result[6] == "" or "simple" in result[6] or "configurable" in result[6]) and result[2] not in ['created_at', 'updated_at']:
                            xml+=""" attrs="{'required':[('exportable','=',True)]}" """
                        if result[3] in ['textarea']:
                            xml+=" colspan='4' nolabel='1' " 
                        xml+=" />\n"
                        
                result = results.pop()
            xml+="</group></page>\n"
        xml+="</notebook>"
        return xml

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context={}, toolbar=False):
        result = super(osv.osv, self).fields_view_get(cr, uid, view_id,view_type,context,toolbar=toolbar)
        if view_type == 'form':
            if context.get('set', False):
                ir_model_id = self.pool.get('ir.model').search(cr, uid, [('model', '=', 'product.product')])[0]
                ir_model = self.pool.get('ir.model').browse(cr, uid, ir_model_id)
                ir_model_field_ids = self.pool.get('ir.model.fields').search(cr, uid, [('model_id', '=', ir_model_id)])
                field_names = ['set']
                for field in self.pool.get('ir.model.fields').browse(cr, uid, ir_model_field_ids):
                    if str(field.name).startswith('x_'):
                        field_names.append(field.name)
                result['fields'].update(self.fields_get(cr, uid, field_names, context))
                result['arch'] = result['arch'].replace('<page string="attributes_placeholder"/>', """<page string="Magento Information" attrs="{'invisible':[('exportable','!=',1)]}"><field name='set' />\n""" + self.redefine_prod_view(cr, uid, field_names, context['set']) + """\n</page>""")
            else:
                result['arch'] = result['arch'].replace('<page string="attributes_placeholder"/>', "")
        return result
    
    #TODO move part of this to declarative mapping CSV template
    def extdata_from_oevals(self, cr, uid, external_referential_id, data_record, mapping_lines, defaults, context):
        product_data = super(product_product, self).extdata_from_oevals(cr, uid, external_referential_id, data_record, mapping_lines, defaults, context) #Aapply custom/attributes mappings

        product = self.browse(cr, uid, data_record['id'], context)
        shop = self.pool.get('sale.shop').browse(cr, uid, context['shop_id'], context)

        if not product_data.get('price', False):
            pl_default_id = shop.pricelist_id and shop.pricelist_id.id or self.pool.get('product.pricelist').search(cr, uid, [('type', '=', 'sale')])
            product_data.update({'price': self.pool.get('product.pricelist').price_get(cr, uid, pl_default_id, product.id, 1.0)[pl_default_id[0]]})
            
        if not product_data.get('tax_class_id', False):
            product_data.update({'tax_class_id': 2}) #FIXME hugly!
            
        if not product_data.get('status', False):
            product_data.update({'status': product.active and 1 or 2})
            
        if not product_data.get('websites', False):
            product_data.update({'websites': [shop.shop_group_id.code]})

        if not product_data.get('description', False):
            product_data.update({'description': product.description or _("description")})
        if not product_data.get('short_description', False):
            product_data.update({'short_description': product.description_sale or _("short description")})
        if not product_data.get('meta_title', False):
            product_data.update({'meta_title': product.name})
        if not product_data.get('meta_keyword', False):
            product_data.update({'meta_keyword': product.name})
        if not product_data.get('meta_description', False):
            product_data.update({'meta_description': product.description_sale and product.description_sale[:255]})
       
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
    
    def _export_inventory(self, cr, uid, product, stock_id, logger, ctx):
        if product.magento_sku and product.type != 'service':
            virtual_available = self.read(cr, uid, product.id, ['virtual_available'], {'location': stock_id})['virtual_available']
            ctx['conn_obj'].call('product_stock.update', [product.magento_sku, {'qty': virtual_available, 'is_in_stock': virtual_available > 0 and 1 or 0}])
            logger.notifyChannel('ext synchro', netsvc.LOG_INFO, "Successfully updated stock level at %s for product with SKU %s " %(virtual_available, product.magento_sku))
    
    def ext_create(self, cr, uid, data, conn, method, oe_id, ctx):        
        product = self.browse(cr, uid, oe_id)
        sku = self.product_to_sku(cr, uid, product)
        shop = self.pool.get('sale.shop').browse(cr, uid, ctx['shop_id'])
        attr_set_id = product.set and self.pool.get('magerp.product_attribute_set').oeid_to_extid(cr, uid, product.set.id, shop.referential_id.id) or ctx.get('default_set_id', 1)
        product_type = 'simple' #TODO FIXME do not hardcode that!

        res = super(magerp_osv.magerp_osv, self).ext_create(cr, uid, [product_type, attr_set_id, sku, data], conn, method, oe_id, ctx)
        self.write(cr, uid, oe_id, {'magento_sku': sku})
        stock_id = shop.warehouse_id.lot_stock_id.id
        logger = netsvc.Logger()
        self._export_inventory(cr, uid, product, stock_id, logger, ctx)
        return res
    
    def ext_update(self, cr, uid, data, conn, method, oe_id, external_id, ir_model_data_id, create_method, ctx):
        product = self.browse(cr, uid, oe_id)
        sku = self.product_to_sku(cr, uid, product)

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
