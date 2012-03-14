# -*- encoding: utf-8 -*-
#########################################################################
#This module intergrates Open ERP with the magento core                 #
#Core settings are stored here                                          #
#########################################################################
#                                                                       #
# Copyright (C) 2009  Sharoon Thomas, Raphaël Valyi                     #
# Copyright (C) 2011 Akretion Sébastien BEAU sebastien.beau@akretion.com#
# Copyright (C) 2011 Camptocamp Guewen Baconnier
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
import pooler
import magerp_osv
from tools.translate import _
import netsvc
import unicodedata
import base64, urllib
import os

from tools import DEFAULT_SERVER_DATETIME_FORMAT

#Enabling this to True will put all custom attributes into One page in
#the products view
GROUP_CUSTOM_ATTRS_TOGETHER = False


#TODO find a good method to replace all of the special caracter allowed by magento as name for product fields
special_character_to_replace = [
    (u"\xf8", u"diam"),
    (u'\xb5', u'micro'),
    (u'\xb2', u'2'),
    (u'\u0153', u'oe'),
]

def convert_to_ascii(my_unicode):
    '''Convert to ascii, with clever management of accents (é -> e, è -> e)'''
    if isinstance(my_unicode, unicode):
        my_unicode_with_ascii_chars_only = ''.join((char for char in unicodedata.normalize('NFD', my_unicode) if unicodedata.category(char) != 'Mn'))
        for special_caracter in special_character_to_replace:
            my_unicode_with_ascii_chars_only = my_unicode_with_ascii_chars_only.replace(special_caracter[0], special_caracter[1])
        return str(my_unicode_with_ascii_chars_only)
    # If the argument is already of string type, we return it with the same value
    elif isinstance(my_unicode, str):
        return my_unicode
    else:
        return False

class magerp_product_category_attribute_options(magerp_osv.magerp_osv):
    _name = "magerp.product_category_attribute_options"
    _description = "Option products category Attributes"
    _rec_name = "label"

    def _get_default_option(self, cr, uid, field_name, value, context=None):
        res = self.search(cr, uid, [['attribute_name', '=', field_name], ['value', '=', value]], context=context)
        return res and res[0] or False


    def get_create_option_id(self, cr, uid, value, attribute_name, context=None):
        id = self.search(cr, uid, [['attribute_name', '=', attribute_name], ['value', '=', value]], context=context)
        if id:
            return id[0]
        else:
            return self.create(cr, uid, {
                                'value': value,
                                'attribute_name': attribute_name,
                                'label': value.replace('_', ' '),
                                }, context=context)

    #TODO to finish : this is just the start of the implementation of attributs for category
    _columns = {
        #'attribute_id':fields.many2one('magerp.product_attributes', 'Attribute'),
        'attribute_name':fields.char(string='Attribute Code',size=64),
        'value':fields.char('Value', size=200),
        #'ipcast':fields.char('Type cast', size=50),
        'label':fields.char('Label', size=100),
    }


magerp_product_category_attribute_options()


class product_category(magerp_osv.magerp_osv):
    _inherit = "product.category"

    def ext_create(self, cr, uid, data, conn, method, oe_id, context=None):
        return conn.call(method, [data.get('parent_id', 1), data])

    _columns = {
        'magerp_fields' : fields.serialized('Magento Product Categories Extra Fields'),
        'create_date': fields.datetime('Created date', readonly=True),
        'write_date': fields.datetime('Updated date', readonly=True),
        'magento_exportable':fields.boolean('Export to Magento'),
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
        'use_default_available_sort_by': fields.boolean('Default Config For Available Sort By', help="Use default config for available sort by"),
        'available_sort_by': fields.sparse(type='many2many', relation='magerp.product_category_attribute_options', string='Available Product Listing (Sort By)', serialization_field='magerp_fields', domain="[('attribute_name', '=', 'sort_by'), ('value', '!=','None')]"),
        'default_sort_by': fields.many2one('magerp.product_category_attribute_options', 'Default Product Listing Sort (Sort By)', domain="[('attribute_name', '=', 'sort_by')]", require=True),
        'magerp_stamp':fields.datetime('Magento stamp'),
        'include_in_menu': fields.boolean('Include in Navigation Menu'),
        'page_layout': fields.many2one('magerp.product_category_attribute_options', 'Page Layout', domain="[('attribute_name', '=', 'page_layout')]"),
        }



    _defaults = {
        'display_mode':lambda * a:'PRODUCTS',
        'use_default_available_sort_by': lambda * a:True,
        'default_sort_by': lambda self,cr,uid,c: self.pool.get('magerp.product_category_attribute_options')._get_default_option(cr, uid, 'sort_by', 'None', context=c),
        'level':lambda * a:1,
        'include_in_menu': lambda * a:True,
        'page_layout': lambda self,cr,uid,c: self.pool.get('magerp.product_category_attribute_options')._get_default_option(cr, uid, 'page_layout', 'None', context=c),
                 }

    def write(self, cr, uid, ids, vals, context=None):
        if not 'magerp_stamp' in vals.keys():
            vals['magerp_stamp'] = time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        return super(product_category, self).write(cr, uid, ids, vals, context)

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

    def ext_export(self, cr, uid, ids, external_referential_ids=None, defaults=None, context=None): # We export all the categories if at least one has been modified since last export
        #TODO Move this function in base_sale_multichannels
        if context is None:
            context = {}

        if defaults is None:
            defaults = {}

        res = False
        ids_exportable = self.search(cr, uid, [('id', 'in', ids), ('magento_exportable', '=', True)]) #restrict export to only exportable products
        ids = [id for id in ids if id in ids_exportable] #we need to kept the order of the categories

        shop = self.pool.get('sale.shop').browse(cr, uid, context['shop_id'])

        context_dic = [context.copy()]
        context_dic[0]['export_url'] = True # for the magento version 1.3.2.4, only one url is autorized by category, so we only export with the MAPPING TEMPLATE the url of the default language
        context_dic[0]['lang'] = shop.referential_id.default_lang_id.code

        for storeview in shop.storeview_ids:
            if storeview.lang_id and storeview.lang_id.code != shop.referential_id.default_lang_id.code:
                context_dic += [context.copy()]
                context_dic[len(context_dic)-1].update({'storeview_code': storeview.code, 'lang': storeview.lang_id.code})

        if shop.last_products_export_date:
            last_exported_time = datetime.datetime.fromtimestamp(time.mktime(time.strptime(shop.last_products_export_date[:19], DEFAULT_SERVER_DATETIME_FORMAT)))
        else:
            last_exported_time = False

        if not last_exported_time:
            for ctx_storeview in context_dic:
                ctx_storeview['force'] = True
                res = super(product_category, self).ext_export(cr, uid, ids, external_referential_ids, defaults, ctx_storeview)
        else:
            cr.execute("select write_date, create_date from product_category where id in %s", (tuple(ids),))
            read = cr.fetchall()
            for categ in read:
                last_updated_categ = categ[0] and categ[0].split('.')[0] or categ[1] and categ[1].split('.')[0] or False
                last_updated_categ_time = datetime.datetime.fromtimestamp(time.mktime(time.strptime(last_updated_categ[:19], DEFAULT_SERVER_DATETIME_FORMAT)))
                if last_updated_categ_time and last_exported_time:
                    if last_exported_time - datetime.timedelta(seconds=1) < last_updated_categ_time:
                        for ctx_storeview in context_dic:
                            ctx_storeview['force'] = True
                            res = super(product_category, self).ext_export(cr, uid, ids, external_referential_ids, defaults, ctx_storeview)
                        break
        return res

    def try_ext_update(self, cr, uid, data, conn, method, oe_id, external_id, ir_model_data_id, create_method, context=None):
        if context is None: context = {}
        if context.get('storeview_code', False):
            return conn.call(method, [external_id, data, context.get('storeview_code', False)])
        else:
            return conn.call(method, [external_id, data])

product_category()


class magerp_product_attributes(magerp_osv.magerp_osv):
    _name = "magerp.product_attributes"
    _description = "Attributes of products"
    _rec_name = "attribute_code"

    def _get_group(self, cr, uid, ids, prop, unknow_none, context=None):
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
                                           ('boolean', 'Yes/No'),
                                           ('date', 'Date'),
                                           ('price', 'Price'),
                                           ('media_image', 'Media Image'),
                                           ('gallery', 'Gallery'),
                                           ('weee', 'Fixed Product Tax'),
                                           ('file', 'File'), #this option is not a magento native field it will be better to found a generic solutionto manage this kind of custom option
                                           ], 'Frontend Input'
                                          ),
        'frontend_class':fields.char('Frontend Class', size=100),
        'backend_model':fields.char('Backend Model', size=200),
        'backend_type':fields.selection([
                                         ('static', 'Static'),
                                         ('varchar', 'Varchar'),
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
        'attribute_set_info':fields.text('Attribute Set Information'),
        'based_on':fields.selection([('product_product', 'Product Product'), ('product_template', 'Product Template')], 'Based On'),
        }

    _defaults = {
        'based_on': lambda*a: 'product_template',
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

    _translatable_default_codes = [
        'description',
        'meta_description',
        'meta_keyword',
        'meta_title',
        'name',
        'short_description',
        'url_key',
    ]

    _not_store_in_json = [
        'minimal_price',
        'special_price',
        'description',
        'meta_description',
        'meta_keyword',
        'meta_title',
        'name',
        'short_description',
        'url_key',
    ]

    _type_conversion = {
        '':'char',
        'text':'char',
        'textarea':'text',
        'select':'many2one',
        'date':'date',
        'price':'float',
        'media_image':'binary',
        'gallery':'binary',
        'multiselect':'many2many',
        'boolean':'boolean',
        'weee':'char',
        False:'char',
        'file':'char', #this option is not a magento native field it will be better to found a generic solutionto manage this kind of custom option
    }

    _type_casts = {
        '':'unicode',
        'text':'unicode',
        'textarea':'unicode',
        'select':'unicode',
        'date':'unicode',
        'price':'float',
        'media_image':'False',
        'gallery':'False',
        'multiselect':'list',
        'boolean':'int',
        'weee':'unicode',
        False:'unicode',
        'file':'unicode', #this option is not a magento native field it will be better to found a generic solutionto manage this kind of custom option
    }

    _variant_fields = [
        'color',
        'dimension',
        'visibility',
    ]

    def _is_attribute_translatable(self, vals):
        """Tells if field associated to attribute should be translatable or not.
        For now we are using a default list, later we could say that any attribute
        which scope in Magento is 'store' should be translated."""
        if vals['attribute_code'] in self._translatable_default_codes:
            return True
        else:
            return False

    def write(self, cr, uid, ids, vals, context=None):
        """Will recreate the mapping attributes, beware if you customized some!"""
        if context is None:
            context = {}

        if type(ids) == int:
            ids = [ids]
        result = super(magerp_product_attributes, self).write(cr, uid, ids, vals, context) 
        model_ids = self.pool.get('ir.model').search(cr, uid, [('model', 'in', ['product.product', 'product.template'])])
        product_model_id = self.pool.get('ir.model').search(cr, uid, [('model', 'in', ['product.product'])])[0]
        referential_id = context.get('referential_id', False)
        for id in ids:
            all_vals = self.read(cr, uid, id, [], context)
            
            #Fetch Options
            if 'frontend_input' in all_vals.keys() and all_vals['frontend_input'] in ['select', 'multiselect']:
                core_imp_conn = self.pool.get('external.referential').connect(cr, uid, [referential_id])
                options_data = core_imp_conn.call('ol_catalog_product_attribute.options', [all_vals['magento_id']])
                if options_data:
                    self.pool.get('magerp.product_attribute_options').data_to_save(cr, uid, options_data, update=True, context={'attribute_id': id, 'referential_id': referential_id})

            
            field_name = all_vals['field_name']
            #TODO refactor me it will be better to add a one2many between the magerp_product_attributes and the ir.model.fields
            field_ids = self.pool.get('ir.model.fields').search(cr, uid, [('name', '=', field_name), ('model_id', 'in', model_ids)])
            if field_ids:
                self._create_mapping(cr, uid, self._type_conversion[all_vals.get('frontend_input', False)], field_ids[0], field_name, referential_id, product_model_id, all_vals, id)
        return result

    def create(self, cr, uid, vals, context=None):
        """Will create product.template new fields accordingly to Magento product custom attributes and also create mappings for them"""
        if context is None:
            context = {}
        if not vals['attribute_code'] in self._no_create_list:
            field_name = "x_magerp_" + vals['attribute_code']
            field_name = convert_to_ascii(field_name)
            vals['field_name']= field_name
        if 'attribute_set_info' in vals.keys():
            attr_set_info = eval(vals.get('attribute_set_info',{}))
            for each_key in attr_set_info.keys():
                vals['group_id'] = attr_set_info[each_key].get('group_id', False)
        
        crid = super(magerp_product_attributes, self).create(cr, uid, vals, context)
        if not vals['attribute_code'] in self._no_create_list:
            #If the field has to be created
            if crid:
                #Fetch Options
                if 'frontend_input' in vals.keys() and vals['frontend_input'] in ['select',  'multiselect']:
                    core_imp_conn = self.pool.get('external.referential').connect(cr, uid, [vals['referential_id']])
                    options_data = core_imp_conn.call('ol_catalog_product_attribute.options', [vals['magento_id']])
                    if options_data:
                        self.pool.get('magerp.product_attribute_options').data_to_save(cr, uid, options_data, update=False, context={'attribute_id': crid, 'referential_id': vals['referential_id']})
      
                #Manage fields
                if vals['attribute_code'] and vals.get('frontend_input', False):
                    #Code for dynamically generating field name and attaching to this
                    if vals['attribute_code'] in self._variant_fields:
                        model_name='product.product'
                    else:
                        model_name='product.template'

                    model_id = self.pool.get('ir.model').search(cr, uid, [('model', '=', model_name)])

                    if model_id and len(model_id) == 1:
                        model_id = model_id[0]
                        #Check if field already exists
                        referential_id = context.get('referential_id',False)
                        field_ids = self.pool.get('ir.model.fields').search(cr, uid, [('name', '=', field_name), ('model_id', '=', model_id)])
                        field_vals = {
                            'name':field_name,
                            'model_id':model_id,
                            'model':model_name,
                            'field_description':vals.get('frontend_label', False) or vals['attribute_code'],
                            'ttype':self._type_conversion[vals.get('frontend_input', False)],
                            'translate': self._is_attribute_translatable(vals),
                        }
                        if not vals['attribute_code'] in self._not_store_in_json:
                            if model_name == 'product.template':
                                field_vals['serialization_field_id'] = self.pool.get('ir.model.fields').search(cr, uid, [('name', '=', 'magerp_tmpl'), ('model', '=', 'product.template')], context=context)[0]
                            else:
                                field_vals['serialization_field_id'] = self.pool.get('ir.model.fields').search(cr, uid, [('name', '=', 'magerp_variant'), ('model', '=', 'product.product')], context=context)[0]
                        if not field_ids:
                            #The field is not there create it
                            #IF char add size
                            if field_vals['ttype'] == 'char':
                                field_vals['size'] = 100
                            if field_vals['ttype'] == 'many2one':
                                field_vals['relation'] = 'magerp.product_attribute_options'
                                field_vals['domain'] = "[('attribute_id','='," + str(crid) + ")]"
                            if field_vals['ttype'] == 'many2many':
                                field_vals['relation'] = 'magerp.product_attribute_options'
                                field_vals['domain'] = "[('attribute_id','='," + str(crid) + ")]"
                            field_vals['state'] = 'manual'
                            #All field values are computed, now save
                            field_id = self.pool.get('ir.model.fields').create(cr, uid, field_vals)
                            # mapping have to be based on product.product
                            model_id = self.pool.get('ir.model').search(cr, uid, [('model', '=', 'product.product')])[0]
                            self._create_mapping(cr, uid, field_vals['ttype'], field_id, field_name, referential_id, model_id, vals, crid)
                            
        return crid

    def _default_mapping(self, cr, uid, ttype, field_name, vals, attribute_id, model_id, referential_id):
        in_function = out_function = False
        if ttype in ['char', 'text', 'date', 'float', 'weee', 'boolean']:
            in_function = "result = [('%s', ifield)]" % (field_name,)
            out_function = "result = [('%s', record['%s'])]" % (vals['attribute_code'], field_name)
        elif ttype in ['many2one']:
            in_function = ("if ifield:\n"
                           "    option_id = self.pool.get('magerp.product_attribute_options').search(cr, uid, [('attribute_id','=',%(attribute_id)s),('value','=',ifield)])\n"
                           "    if option_id:\n"
                           "        result = [('%(field_name)s', option_id[0])]")  % ({'attribute_id': attribute_id, 'field_name': field_name})
            # we browse on record['%(field_name)s'][0] because record[field_name] is in the form (id, name)
            out_function = ("result = [('%(attribute_code)s', False)]\n"
                            "if record.get('%(field_name)s'):\n"
                            "    option = self.pool.get('magerp.product_attribute_options').browse(cr, uid, record['%(field_name)s'][0])\n"
                            "    if option:\n"
                            "        result = [('%(attribute_code)s', option.value)]") % ({'field_name': field_name, 'attribute_code': vals['attribute_code']})
        elif ttype in ['many2many']:
            in_function = ("option_ids = []\n"
                           "opt_obj = self.pool.get('magerp.product_attribute_options')\n"
                           "for ext_option_id in ifield:\n"
                           "    option_ids.extend(opt_obj.search(cr, uid, [('attribute_id','=',%(attribute_id)s), ('value','=',ext_option_id)]))\n"
                           "result = [('%(field_name)s', [(6, 0, option_ids)])]") % ({'attribute_id': attribute_id, 'field_name': field_name})
            out_function = ("result=[('%(attribute_code)s', [])]\n"
                            "if record.get('%(field_name)s'):\n"
                            "    options = self.pool.get('magerp.product_attribute_options').browse(cr, uid, record['%(field_name)s'])\n"
                            "    result = [('%(attribute_code)s', [option.value for option in options])]") % \
                           ({'field_name': field_name, 'attribute_code': vals['attribute_code']})
        elif ttype in ['binary']:
            logger = netsvc.Logger()
            warning_text = "Binary mapping is actually not supported (attribute: %s)" % (vals['attribute_code'],)
            logger.notifyChannel('ext synchro mapping', netsvc.LOG_WARNING, warning_text)
            warning_msg = ("import netsvc\n"
                           "logger = netsvc.Logger()\n"
                           "logger.notifyChannel('ext synchro mapping', netsvc.LOG_WARNING, '%s')") % (warning_text,)
            in_function = out_function = warning_msg
        return in_function, out_function

    def _create_mapping(self, cr, uid, ttype, field_id, field_name, referential_id, model_id, vals, attribute_id):
        """Search & create mapping entries"""
        if vals['attribute_code'] in self._no_create_list:
            return False
        mapping_id = self.pool.get('external.mapping').search(cr, uid, [('referential_id', '=', referential_id), ('model_id', '=', model_id)])
        if mapping_id:
            existing_line = self.pool.get('external.mapping.line').search(cr, uid, [('external_field', '=', vals['attribute_code']), ('mapping_id', '=', mapping_id[0])])
            if not existing_line:
                mapping_line = {'external_field': vals['attribute_code'],
                                'mapping_id': mapping_id[0],
                                'type': 'in_out',
                                'external_type': self._type_casts[vals.get('frontend_input', False)],
                                'field_id': field_id, }
                mapping_line['in_function'], mapping_line['out_function'] = self._default_mapping(cr, uid, ttype, field_name, vals, attribute_id, model_id, referential_id)
                self.pool.get('external.mapping.line').create(cr, uid, mapping_line)
        return True

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

    def data_to_save(self, cr, uid, vals_list, update=False, context=None):
        """This method will take data from vals and use context to create record"""
        
        if context is None:
            context = {}
        to_remove_ids = []
        if update:
            to_remove_ids = self.search(cr, uid, [('attribute_id', '=', context['attribute_id'])])
        
        for vals in vals_list:
            if vals.get('value', False) and vals.get('label', False):
                #Fixme: What to do when Magento offers emty options which open erp doesnt?
                #Such cases dictionary is: {'value':'','label':''}
                if update:
                    existing_ids = self.search(cr, uid, [('attribute_id', '=', context['attribute_id']), ('label', '=', vals['label'])])
                    if len(existing_ids) == 1:
                        to_remove_ids.remove(existing_ids[0])
                        self.write(cr, uid, existing_ids[0], {'value': vals.get('value', False)})
                        continue

                self.create(cr, uid, {
                                        'attribute_id': context['attribute_id'],
                                        'value': vals['value'],
                                        'label': vals['label'],
                                        'referential_id': context['referential_id'],
                                    }
                            )

        self.unlink(cr, uid, to_remove_ids) #if a product points to a removed option, it will get no option instead

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
        #print attr_set_list_oe
        for each_set in attr_set_list_oe:
            attr_set_list[each_set['magento_id']] = each_set['id']
        key_attrs = []
        #print mage_inp
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
    
magerp_product_attribute_set()

class magerp_product_attribute_groups(magerp_osv.magerp_osv):
    _name = "magerp.product_attribute_groups"
    _description = "Attribute groups in Magento"
    _rec_name = 'attribute_group_name'
    _order = "sort_order"
    def _get_set(self, cr, uid, ids, prop, unknow_none, context=None):
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

class product_product_type(osv.osv):
    _name = 'magerp.product_product_type'
    _columns = {
        'name': fields.char('Name', size=100, required=True, translate=True),
        'product_type': fields.char('Type', size=100, required=True, help="Use the same name of Magento product type, for example 'simple'."),
        'default_type': fields.selection([('product','Stockable Product'),('consu', 'Consumable'),('service','Service')], 'Default Product Type', required=True, help="Default product's type (Procurement) when a product is imported from Magento."),
    }
product_product_type()



class product_mag_osv(magerp_osv.magerp_osv):
    _register = False # Set to false if the model shouldn't be automatically discovered.
    
    #remember one thing in life: Magento lies: it tells attributes are required while they are awkward to fill
    #and will have a nice default vaule anyway, that's why we avoid making them mandatory in the product view
    _magento_fake_mandatory_attrs = ['created_at', 'updated_at', 'has_options', 'required_options', 'model']

    def open_magento_fields(self, cr, uid, ids, context=None):
        ir_model_data_obj = self.pool.get('ir.model.data')
        ir_model_data_id = ir_model_data_obj.search(cr, uid, [['model', '=', 'ir.ui.view'], ['name', '=', self._name.replace('.','_') + '_wizard_form_view_magerpdynamic']], context=context)
        if ir_model_data_id:
            res_id = ir_model_data_obj.read(cr, uid, ir_model_data_id, fields=['res_id'])[0]['res_id']
        set_id = self.read(cr, uid, ids, fields=['set'], context=context)[0]['set']

        if not set_id:
            raise osv.except_osv(_('User Error'), _('Please chose an attribut set before'))

        return {
            'name': 'Magento Fields',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': [res_id],
            'res_model': self._name,
            'context': "{'set': %s, 'open_from_button_object_id': %s}"%(set_id[0], ids),
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'res_id': ids and ids[0] or False,
        }

    def save_and_close_magento_fields(self, cr, uid, ids, context=None):
        '''this empty function will save the magento field'''
        return {'type': 'ir.actions.act_window_close'}

    def redefine_prod_view(self,cr,uid, field_names, context=None):
        def clean_for_xml(string):
            for key, key_replace in [('&', '&amp;'), ('>','&gt;'),  ('<', '&lt;')]:
                string = string.replace(key, key_replace)
            return string
        #This function will rebuild the view for product from instances, attribute groups etc
        #Get all objects needed
        #inst_obj = self.pool.get('external.referential')
        if context is None: context = {}
        attr_set_obj = self.pool.get('magerp.product_attribute_set')
        attr_group_obj = self.pool.get('magerp.product_attribute_groups')
        attr_obj = self.pool.get('magerp.product_attributes')
        translation_obj = self.pool.get('ir.translation')
        xml = u"<notebook colspan='4'>\n"
        attr_grp_ids = attr_group_obj.search(cr,uid,[])
        attr_groups = attr_group_obj.browse(cr,uid,attr_grp_ids)
        attribute_set_id = context['set']
        attr_set = attr_set_obj.browse(cr, uid, attribute_set_id)
        attr_group_fields_rel = {}
        cr.execute("select attr_id, group_id, attribute_code, frontend_input, frontend_label, is_required, apply_to, field_name  from magerp_attrset_attr_rel left join magerp_product_attributes on magerp_product_attributes.id = attr_id where magerp_attrset_attr_rel.set_id=%s" % attribute_set_id)
        results = cr.fetchall()
        result = results.pop()
        while len(results) > 0:
            mag_group_id = result[1]
            oerp_group_id = attr_group_obj.extid_to_oeid(cr, uid, mag_group_id, attr_set.referential_id.id)
            if not oerp_group_id: #FIXME workaround in multi-Magento instances (databases) where attribute group might not be found due to the way we share attributes currently
                for ref_id in self.pool.get('external.referential').search(cr, uid, []):
                     if ref_id != attr_set.referential_id.id:
                         oerp_group_id = attr_group_obj.extid_to_oeid(cr, uid, mag_group_id, ref_id)
                         if oerp_group_id:
                             break
            group_name = attr_group_obj.read(cr, uid, oerp_group_id, ['attribute_group_name'])['attribute_group_name']
            
            #Create a page for the attribute group
            if not attr_group_fields_rel.get(group_name, False):
                attr_group_fields_rel[group_name] = []
            while True:
                field_xml=""
                if result[1] != mag_group_id:
                    break
                if result[7] in field_names:
                    if not result[2] in attr_obj._no_create_list:
                        if result[3] in ['textarea']:
                            trans = translation_obj._get_source(cr, uid, 'product.product', 'view', context.get('lang', ''), result[4])
                            trans = trans or result[4]
                            field_xml+="<newline/><separator colspan='4' string='%s'/>" % (clean_for_xml(trans),)
                        field_xml+="<field name='" +  clean_for_xml(result[7]) + "'"
                        if result[5] and (result[6] == "" or "simple" in result[6] or "configurable" in result[6]) and result[2] not in self._magento_fake_mandatory_attrs:
                            field_xml+=""" attrs="{'required':[('magento_exportable','=',True)]}" """
                        if result[3] in ['textarea']:
                            field_xml+=" colspan='4' nolabel='1' " 
                        field_xml+=" />\n"
                        if (group_name in  [
                                            u'Meta Information', 
                                            u'General', 
                                            u'Custom Layout Update', 
                                            u'Prices', 
                                            u'Design', 
                                            ]) or GROUP_CUSTOM_ATTRS_TOGETHER==False:
                            attr_group_fields_rel[group_name].append(field_xml)
                        else:
                            custom_attributes = attr_group_fields_rel.get(u"Custom Attributes",[])
                            custom_attributes.append(field_xml)
                            attr_group_fields_rel[u"Custom Attributes"] = custom_attributes
                if len(results) > 0:
                    result = results.pop()
                else:
                    break
        attribute_groups = attr_group_fields_rel.keys()
        attribute_groups.sort()
        for each_attribute_group in attribute_groups:
            trans = translation_obj._get_source(cr, uid, 'product.product', 'view', context.get('lang', ''), each_attribute_group)
            trans = trans or each_attribute_group
            if attr_group_fields_rel.get(each_attribute_group,False):
                xml+="<page string='" + clean_for_xml(trans) + "'>\n<group colspan='4' col='4'>"
                xml+="\n".join(attr_group_fields_rel.get(each_attribute_group,[]))
                xml+="</group></page>\n"
        if context.get('multiwebsite', False):
            xml+="""<page string='Websites'>\n<field name='websites_ids' nolabel="1"/>\n</page>\n"""
        xml+="</notebook>"
        return xml
    
    def _filter_fields_to_return(self, cr, uid, field_names, context=None):
        '''This function is a hook in order to filter the fields that appears on the view'''
        return field_names

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if context is None:
            context = {}
        result = super(product_mag_osv, self).fields_view_get(cr, uid, view_id,view_type,context,toolbar=toolbar)
        print 'fields view get', result
        if view_type == 'form':
            result['arch'] = result['arch'].decode('utf8') #in order to support special character, the arch for the product view will be a unicode and not a str
            if context.get('set', False):
                models = ['product.template']
                if self._name == 'product.product':
                    models.append('product.product')
                ir_model_ids = self.pool.get('ir.model').search(cr, uid, [('model', 'in', models)])
                ir_model_field_ids = self.pool.get('ir.model.fields').search(cr, uid, [('model_id', 'in', ir_model_ids)])
                field_names = ['product_type']
                for field in self.pool.get('ir.model.fields').browse(cr, uid, ir_model_field_ids):
                    if field.name.startswith('x_'):
                        field_names.append(field.name)
                if len(self.pool.get('external.shop.group').search(cr,uid,[('referential_type', 'ilike', 'mag')])) >1 :
                    context['multiwebsite'] = True
                    field_names.append('websites_ids')
                    
                field_names = self._filter_fields_to_return(cr, uid, field_names, context)
                result['fields'].update(self.fields_get(cr, uid, field_names, context))

                view_part = self.redefine_prod_view(cr, uid, field_names, context)
                if '<page string="attributes_placeholder"/>' in result['arch']:
                    # If the view have the tag '<page string="attributes_placeholder"/>' the view asked is the main view
                    # Else it's the pop up with specific fields
                    magento_tab = (
                        "<page string='" + _('Magento Information') + " ' attrs=\"{'invisible':[('magento_exportable','!=',1)]}\">"
                            "<field name='product_type' attrs=\"{'required':[('magento_exportable','=',True)]}\"/>\n"
                            + view_part +
                        "</page>"
                        )
                    result['arch'] = result['arch'].replace('<page string="attributes_placeholder"/>', magento_tab)
                    result['arch'] = result['arch'].replace('<button name="open_magento_fields"/>', '')
                else:
                    result['arch'] = result['arch'].replace('<separator string="attributes_placeholder" colspan="4"/>', view_part)
            else:
                magento_button = (
                    "<button name='open_magento_fields' string='Open Magento Fields' icon='gtk-go-forward' type='object'"
                    " colspan='2' attrs=\"{'invisible':[('magento_exportable','!=', True)]}\""
                    )
                result['arch'] = result['arch'].replace('<button name="open_magento_fields"', magento_button)
                result['arch'] = result['arch'].replace('<page string="attributes_placeholder"/>', "")
        return result

class product_template(product_mag_osv):
    _inherit = "product.template"

    _columns = {
        'magerp_tmpl' : fields.serialized('Magento Template Fields'),
        'set':fields.many2one('magerp.product_attribute_set', 'Attribute Set'),
        'websites_ids': fields.many2many('external.shop.group', 'magerp_product_shop_group_rel', 'product_id', 'shop_group_id', 'Websites', help='By defaut product will be exported on every website, if you want to export it only on some website select them here'),
    }

product_template()


class product_product(product_mag_osv):
    _inherit = "product.product"

    #TODO base the import on the mapping and the function ext_import
    def import_product_image(self, cr, uid, id, referential_id, conn, ext_id=None, context=None):
        image_obj = self.pool.get('product.images')
        logger = netsvc.Logger()
        if not ext_id:
            ext_id = self.oeid_to_extid(cr, uid, id, referential_id, context=None)
        # TODO everythere will should pass the params 'id' for magento api in order to force 
        # to use the id as external key instead of mixed id/sku
        img_list = conn.call('catalog_product_attribute_media.list', [ext_id, False, 'id'])
        logger.notifyChannel('ext synchro', netsvc.LOG_INFO, "Magento image for product ext_id %s: %s" %(ext_id, img_list))
        images_name = []
        for image in img_list:
            img=False
            try:
                (filename, header) = urllib.urlretrieve(image['url'])
                f = open(filename , 'rb')
                data = f.read()
                f.close()
                if "DOCTYPE html PUBLIC" in data:
                    logger.notifyChannel('ext synchro', netsvc.LOG_WARNING, "failed to open the image %s from Magento" % (image['url'],))
                    continue
                else:
                    img = base64.encodestring(data)
            except Exception, e:
                #TODO raise correctly the error
                logger.notifyChannel('ext synchro', netsvc.LOG_WARNING, "failed to open the image %s from Magento, error : %s" % (image['url'],e))
                continue
            mag_filename, extention = os.path.splitext(os.path.basename(image['file']))
            data = {'name': image['label'] and not image['label'] in images_name and image['label'] or mag_filename,
                'extention': extention,
                'link': False,
                'file': img,
                'product_id': id,
                'small_image': image['types'].count('small_image') == 1,
                'base_image': image['types'].count('image') == 1,
                'thumbnail': image['types'].count('thumbnail') == 1,
                'exclude': bool(eval(image['exclude'] or 'False')),
                'position': image['position']
                }
            #the character '/' is not allowed in the name of the image
            data['name'] = data['name'].replace('/', ' ')
            images_name.append(data['name'])
            image_oe_id = image_obj.extid_to_existing_oeid(cr, uid, image['file'], referential_id, context=None)
            if image_oe_id:
                # update existing image
                image_obj.write(cr, uid, image_oe_id, data, context=context)
            else:
                # create new image
                new_image_id = image_obj.create(cr, uid, data, context=context)
                image_obj.create_external_id_vals(cr, uid, new_image_id, image['file'], referential_id, context=context)
        return True
    
    def extid_to_existing_oeid(self, cr, uid, id, external_referential_id, context=None):
        """Returns the OpenERP id of a resource by its external id.
           Returns False if the resource does not exist."""
        if not context:
            context={}
        res = super(product_mag_osv, self).extid_to_existing_oeid(cr, uid, id, external_referential_id, context=context)
        # TODO : check if this can be replaced by _existing_oeid_for_extid_import (see example in res.partner)
        # thus when importing a product which do not already exists in OpenERP, ext_import will create the binding and update it directly
        if not res and context.get('magento_sku', False):
            product_id = self.search(cr, uid, [('magento_sku', '=', context['magento_sku'])], context=context)
            return product_id and product_id[0] or False
        return res

    def _product_type_get(self, cr, uid, context=None):
        ids = self.pool.get('magerp.product_product_type').search(cr, uid, [], order='id')
        product_types = self.pool.get('magerp.product_product_type').read(cr, uid, ids, ['product_type','name'], context=context)
        return [(pt['product_type'], pt['name']) for pt in product_types]

    def _is_magento_exported(self, cr, uid, ids, field_name, arg, context=None):
        """Return True if the product is already exported to at least one magento shop
        """
        res = {}
        # get all magento external_referentials
        referentials = self.pool.get('external.referential').search(cr, uid, [('magento_referential', '=', True)])
        for product in self.browse(cr, uid, ids, context):
            for referential in referentials:
                res[product.id] = False
                if self.oeid_to_extid(cr, uid, product.id, referential, context):
                    res[product.id] = True
                    break
        return res

    _columns = {
        'magerp_variant' : fields.serialized('Magento Variant Fields'),
        'magento_sku':fields.char('Magento SKU', size=64),
        'magento_exportable':fields.boolean('Exported to Magento?'),
        'created_at':fields.date('Created'), #created_at & updated_at in magento side, to allow filtering/search inside OpenERP!
        'updated_at':fields.date('Created'),
        'tier_price':fields.one2many('product.tierprice', 'product', 'Tier Price'),
        'product_type': fields.selection(_product_type_get, 'Product Type'),
        'magento_exported': fields.function(_is_magento_exported, type="boolean", method=True, string="Exists on Magento"),  # used to set the sku readonly when already exported
        }

    _defaults = {
        'magento_exportable':lambda * a:True
    }

    _sql_constraints = [
        ('magento_sku_uniq', 'unique (magento_sku)', 'The Magento SKU should be uniq!'),
    ]

    def write(self, cr, uid, ids, vals, context=None):
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
    
    def create(self, cr, uid, vals, context=None):
        tier_price = False
        if vals.get('referential_id', False):
            instance = vals['referential_id']
            #Filter keys to be changed
            if 'x_magerp_tier_price' in vals.keys(): 
                tier_price = vals.pop('x_magerp_tier_price')

        crid = super(product_product, self).create(cr, uid, vals, context)
        #Save the tier price
        if tier_price:
            self.create_tier_price(cr, uid, tier_price, instance, crid)
        #Perform other operations
        return crid

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}

        default['magento_exportable'] = False
        default['magento_sku'] = False

        return super(product_product, self).copy(cr, uid, id, default=default, context=context)

    def unlink(self, cr, uid, ids, context=None):
        #if product is mapped to magento, not delete it
        not_delete = False
        sale_obj = self.pool.get('sale.shop')
        search_params = [
            ('magento_shop', '=', True),
        ]
        shops_ids = sale_obj.search(cr, uid, search_params)

        for shop in sale_obj.browse(cr, uid, shops_ids, context):
            for product_id in ids:
                mgn_product = self.oeid_to_extid(cr, uid, product_id, shop.referential_id.id)
                if mgn_product:
                    not_delete = True
                    break
        if not_delete:
            if len(ids) > 1:
                raise osv.except_osv(_('Warning!'), _('They are some products related to Magento. They can not be deleted!\nYou can change their Magento status to "Disabled" and uncheck the active box to hide them from OpenERP.'))
            else:
                raise osv.except_osv(_('Warning!'), _('This product is related to Magento. It can not be deleted!\nYou can change it Magento status to "Disabled" and uncheck the active box to hide it from OpenERP.'))
        else:
            return super(product_product, self).unlink(cr, uid, ids, context)
    
    #TODO move part of this to declarative mapping CSV template
    def extdata_from_oevals(self, cr, uid, external_referential_id, data_record, mapping_lines, defaults, context=None):
        product_data = super(product_product, self).extdata_from_oevals(cr, uid, external_referential_id, data_record, mapping_lines, defaults, context) #Aapply custom/attributes mappings
        if context is None: context = {}
        product = self.browse(cr, uid, data_record['id'], context)
        shop = self.pool.get('sale.shop').browse(cr, uid, context['shop_id'], context)

        if not product_data.get('price', False):
            pl_default_id = shop.pricelist_id and shop.pricelist_id.id or self.pool.get('product.pricelist').search(cr, uid, [('type', '=', 'sale')])
            if isinstance(pl_default_id, int):
                pl_default_id = [pl_default_id]
            product_data.update({'price': self.pool.get('product.pricelist').price_get(cr, uid, pl_default_id, product.id, 1.0)[pl_default_id[0]]})
            
        if not product_data.get('tax_class_id', False):
            product_data.update({'tax_class_id': 2}) #FIXME hugly!
            
        if not product_data.get('status', False):
            product_data.update({'status': product.active and 1 or 0})

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

    def oevals_from_extdata(self, cr, uid, external_referential_id, data_record, key_field, mapping_lines, defaults, context):
        res = super(product_product, self).oevals_from_extdata(cr, uid, external_referential_id, data_record, key_field, mapping_lines, defaults, context)

        # assign a default product type (Procurement, not the magento's one)
        if not res.get('type'):
            magerp_type_obj = self.pool.get('magerp.product_product_type')
            magerp_type_ids = magerp_type_obj.search(cr, uid, [('product_type', '=', data_record['type_id'])], context=context)
            if magerp_type_ids:
                res['type'] = magerp_type_obj.read(cr, uid, magerp_type_ids[0], ['default_type'], context=context)['default_type']
        return res

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

    def ext_create(self, cr, uid, data, conn, method, oe_id, context=None):
        if context is None: context = {}
        product = self.browse(cr, uid, oe_id, context=context)
        sku = self.product_to_sku(cr, uid, product)
        shop = self.pool.get('sale.shop').browse(cr, uid, context['shop_id'])
        attr_set_id = product.set and self.pool.get('magerp.product_attribute_set').oeid_to_extid(cr, uid, product.set.id, shop.referential_id.id) or context.get('default_set_id', 1)
        
        product_type = self.read(cr, uid, oe_id, ['product_type'])['product_type'] or 'simple'

        res = super(magerp_osv.magerp_osv, self).ext_create(cr, uid, [product_type, attr_set_id, sku, data], conn, method, oe_id, context)
        self.write(cr, uid, oe_id, {'magento_sku': sku})
        return res
    
    def action_before_exporting_grouped_product(self, cr, uid, id, external_referential_ids=None, defaults=None, context=None):
        logger = netsvc.Logger()
        if context.get('mrp_is_installed', False):
            bom_ids = self.read(cr, uid, id, ['bom_ids'])['bom_ids']
            if len(bom_ids): # it has or is part of a BoM
                cr.execute("SELECT product_id, product_qty FROM mrp_bom WHERE bom_id = %s", (bom_ids[0],)) #FIXME What if there is more than a materials list?
                results = cr.fetchall()
                child_ids = []
                quantities = {}
                for x in results:
                    child_ids += [x[0]]
                    sku = self.read(cr, uid, x[0], ['magento_sku'])['magento_sku']
                    quantities.update({sku: x[1]})
                if child_ids: #it is an assembly and it contains the products child_ids: 
                    self.ext_export(cr, uid, child_ids, external_referential_ids, defaults, context) #so we export them
        else:
            logger.notifyChannel('ext synchro', netsvc.LOG_ERROR, "OpenERP 'grouped' products will export to Magento as 'grouped products' only if they have a BOM and if the 'mrp' BOM module is installed")
        return quantities, child_ids

    def action_before_exporting(self, cr, uid, id, product_type, external_referential_ids=None, defaults=None, context=None):
        '''Hook to allow your external module to execute some code before exporting a product'''
        return True
    
    #todo move this code to a generic module
    def get_last_update_date(self, cr, uid, product_read, context=None):
        """if a product have a depends on other object like bom for grouped product, or other product for configurable
        the date of last update should be based on the last update of the dependence object"""
        conn = context.get('conn_obj', False)
        last_updated_date = product_read['write_date'] or product_read['create_date'] or False
        if product_read['product_type'] == 'grouped':
            if context.get('mrp_is_installed', False):
                #TODO improve this part of code as the group product can be based on nan_product_pack
                cr.execute("select id, write_date, create_date from mrp_bom where product_id = %s", (product_read['id'],))
                read_bom = cr.dictfetchall()
                for bom in read_bom:
                    last_updated_bom_date = bom['write_date'] or bom['create_date'] or False
                    if last_updated_bom_date > last_updated_date:
                        last_updated_date=last_updated_bom_date
            else:
                conn.logger.notifyChannel('ext synchro', netsvc.LOG_ERROR, "OpenERP 'grouped' products will export to Magento as 'grouped products' only if they have a BOM and if the 'mrp' BOM module is installed")   
        return last_updated_date
                    
    
    def get_ordered_ids(self, cr, uid, ids, external_referential_ids=None, defaults=None, context=None):
        #TODO pass the shop better than the referentials
        dates_2_ids = []
        ids_2_dates = {}
        shop = self.pool.get('sale.shop').browse(cr, uid, context['shop_id'])
        if shop.last_products_export_date:
            last_exported_date = shop.last_products_export_date
        else:
            last_exported_date = False
        #strangely seems that on inherits structure, write_date/create_date are False for children
        #TODO check previous comment and check the write date on product template also for variant of product
        cr.execute("select id, write_date, create_date, product_type from product_product where id in %s", (tuple(ids),))
        read = cr.dictfetchall()
        ids = []
        context['force']=True
        
        for product_read in read:
            last_updated_date = self.get_last_update_date(cr, uid, product_read, context=context)
            if last_exported_date and last_updated_date < last_exported_date:
                continue
            dates_2_ids += [(last_updated_date, product_read['id'])]
            ids_2_dates[product_read['id']] = last_updated_date

        dates_2_ids.sort()
        ids = [x[1] for x in dates_2_ids]

        return ids, ids_2_dates
        

    def ext_export(self, cr, uid, ids, external_referential_ids=None, defaults=None, context=None):
        #check if mrp is installed
        cr.execute('select * from ir_module_module where name=%s and state=%s', ('mrp','installed'))
        data_record = cr.fetchone()
        if data_record and 'mrp' in data_record:
            context['mrp_is_installed']=True

        if context is None:
            context = {}

        if defaults is None:
            defaults = {}
        #TODO Is external_referential_ids is still used?
        if external_referential_ids is None:
            external_referential_ids = []

        result = {'create_ids':[], 'write_ids':[]}
        shop = self.pool.get('sale.shop').browse(cr, uid, context['shop_id'])
        context['external_referential_id']=shop.referential_id.id
        #TODO It will be better if this check was done before
        ids = self.search(cr, uid, [('id', 'in', ids), ('magento_exportable', '=', True)]) #restrict export to only exportable products
        if not ids:
            return result
        
        if not context.get('force_export', False):
            ids, ids_2_dates = self.get_ordered_ids(cr, uid, ids, external_referential_ids, defaults, context)

        #set the default_set_id in context and avoid extra request for each product upload
        
        conn = context.get('conn_obj', False)
        attr_sets = conn.call('product_attribute_set.list')
        default_set_id = 1
        for attr_set in attr_sets:
            if attr_set['name'] == 'Default':
                default_set_id = attr_set['set_id']
                break
        context['default_set_id'] = default_set_id
        
        context_dic = [context.copy()]
        context_dic[0]['export_url'] = True # for the magento version 1.3.2.4, only one url is autorized by product, so we only export with the MAPPING TEMPLATE the url of the default language 
        context_dic[0]['lang'] = shop.referential_id.default_lang_id.code

        for storeview in shop.storeview_ids:
            if storeview.lang_id and storeview.lang_id.code != shop.referential_id.default_lang_id.code:
                context_dic += [context.copy()]
                context_dic[len(context_dic)-1].update({'storeview_code': storeview.code, 'lang': storeview.lang_id.code})

        for id in ids:
            child_ids = []
            product_type = self.read(cr, uid, id, ['product_type'])['product_type']
            if product_type == 'grouped': # lookup for Magento "grouped product"
                quantities, childs_ids = self.action_before_exporting_grouped_product(cr, uid, id, external_referential_ids, defaults, context)
            
            self.action_before_exporting(cr, uid, id, product_type, external_referential_ids, defaults, context=context)
            
            for context_storeview in context_dic:
                temp_result = super(magerp_osv.magerp_osv, self).ext_export(cr, uid, [id], external_referential_ids, defaults, context_storeview)
                #TODO maybe refactor this part, did we need to assign and make the link for every store?
                if child_ids:
                    self.ext_product_assign(cr, uid, 'grouped', id, child_ids, quantities=quantities, external_referential_ids=external_referential_ids, defaults=defaults, context=context_storeview)
                self.ext_assign_links(cr, uid, id, external_referential_ids=external_referential_ids, defaults=defaults, context=context_storeview)
            not context.get('force_export', False) and self.pool.get('sale.shop').write(cr, uid,context['shop_id'], {'last_products_export_date': ids_2_dates[id]})
            result['create_ids'] += temp_result['create_ids']
            result['write_ids'] += temp_result['write_ids']
        return result
    
    def try_ext_update(self, cr, uid, data, conn, method, oe_id, external_id, ir_model_data_id, create_method, context=None):
        if context is None: context = {}
        if context.get('storeview_code', False):
            return conn.call(method, [external_id, data, context.get('storeview_code', False)])
        else:
            return conn.call(method, [external_id, data])
    
    def ext_update(self, cr, uid, data, conn, method, oe_id, external_id, ir_model_data_id, create_method, context=None):
        product = self.browse(cr, uid, oe_id)
        sku = self.product_to_sku(cr, uid, product)
        return super(magerp_osv.magerp_osv, self).ext_update(cr, uid, data, conn, method, oe_id, sku, ir_model_data_id, create_method, context)

    def _prepare_inventory_magento_vals(self, cr, uid, product, stock, shop,
                                        context=None):
        """
        Prepare the values to send to Magento (message product_stock.update).
        Can be inherited to customize the values to send.

        :param browse_record product: browseable product
        :param browse_record stock: browseable stock location
        :param browse_record shop: browseable shop
        :return: a dict of values which will be sent to Magento with a call to:
        product_stock.update
        """
        stock_field = (shop.product_stock_field_id and
                       shop.product_stock_field_id.name or
                       'virtual_available')
        stock_quantity = product[stock_field]
        return {'qty': stock_quantity,
                # put the stock availability to "out of stock"
                'is_in_stock': int(stock_quantity > 0)}

    def export_inventory(self, cr, uid, ids, shop_id,
                         connection, context=None):
        """
        Export to Magento the stock quantity for the products in ids which
        are already exported on Magento and are not service products.

        :param int shop_id: id of the shop where the stock inventory has
        to be exported
        :param Connection connection: connection object
        :return: True
        """
        if context is None: context = {}
        logger = netsvc.Logger()

        shop = self.pool.get('sale.shop').browse(
            cr, uid, shop_id, context=context)
        referential = shop.referential_id

        # exclude service products
        stock_product_ids = self.search(
            cr, uid,
            [('id', 'in', ids),
             ('type', '!=', 'service'),
             ('magento_exportable', '=', True)],
            context=context)

        # use the stock location defined on the sale shop
        # to compute the stock value
        stock = shop.warehouse_id.lot_stock_id
        location_ctx = context.copy()
        location_ctx['location'] = stock.id
        products = self.browse(
            cr, uid, stock_product_ids, context=location_ctx)

        for product in products:
            mag_product_id = self.oeid_to_extid(
                cr, uid, product.id, referential.id, context=context)
            if not mag_product_id:
                continue  # skip products which are not exported
            inventory_vals = self._prepare_inventory_magento_vals(
                cr, uid, product, stock, shop, context=location_ctx)

            connection.call('product_stock.update',
                            [mag_product_id, inventory_vals])

            logger.notifyChannel(
                'ext synchro',
                netsvc.LOG_INFO,
                "Successfully updated stock level at %s for "
                "product with SKU %s " %
                (inventory_vals['qty'], product.magento_sku))
        return True
    
    def ext_assign_links(self, cr, uid, ids, external_referential_ids=None, defaults=None, context=None):
        """ Assign links of type up-sell, cross-sell, related """
        if isinstance(ids, (int, long)):
            ids = [ids]
        for product in self.browse(cr, uid, ids, context):
            for type_selection in self.pool.get('product.link').get_link_type_selection(cr, uid, context):
                link_type = type_selection[0]
                position = {}
                linked_product_ids = []
                for link in product.product_link_ids:
                    if link.type == link_type:
                        linked_product_ids.append(link.linked_product_id.id)
                        position[link.linked_product_id.magento_sku] = link.sequence
                self.ext_product_assign(cr, uid, link_type, product.id, linked_product_ids, position=position,
                                        external_referential_ids=external_referential_ids, defaults=defaults, context=context)
        return True

    def ext_product_assign(self, cr, uid, type, parent_id, child_ids, quantities=None, position=None, external_referential_ids=None, defaults=None, context=None):
        context = context or {}
        position = position or {}
        quantities = quantities or {}
        external_referential_ids = external_referential_ids or []
        logger = netsvc.Logger()
        conn = context.get('conn_obj', False)

        # ensure that the product to link is exported before assigning it, export it if necessary
        for external_referential_id in external_referential_ids:
            ids_to_export = []
            for child_id in child_ids:
                if not self.oeid_to_extid(cr, uid, child_id, external_referential_id, context=context):
                    ids_to_export.append(child_id)
            export_ctx = context.copy()
            export_ctx['force_export'] = True
            self.ext_export(cr, uid, ids_to_export, [external_referential_id], defaults, export_ctx)

        parent_sku = self.read(cr, uid, parent_id, ['magento_sku'])['magento_sku']
        new_child_skus = self.read(cr, uid, child_ids, ['magento_sku']) # get the sku of the products to be assigned
        new_child_skus = [x['magento_sku'] for x in new_child_skus]
        
        data = [type, parent_sku]
        child_list = conn.call('product_link.list', data) # get the sku of the products already assigned
        old_child_skus = [x['sku'] for x in child_list]
        skus_to_remove = []
        skus_to_assign = []
        skus_to_update = []
        for old_child_sku in old_child_skus:
            if old_child_sku not in new_child_skus:
                skus_to_remove += [old_child_sku]
        for new_child_sku in new_child_skus:
            if new_child_sku in old_child_skus:
                skus_to_update += [new_child_sku]
            else:
                skus_to_assign += [new_child_sku]
        for old_child_sku in skus_to_remove:
            conn.call('product_link.remove', data + [old_child_sku]) # remove the products that are no more used
            logger.notifyChannel('ext assign', netsvc.LOG_INFO, "Successfully removed assignment of type %s for product %s to product %s" % (type, parent_sku, old_child_sku))
        for child_sku in skus_to_assign:
            conn.call('product_link.assign', data + [child_sku, {'position': position.get(child_sku, 0), 'qty': quantities.get(child_sku, 1)}]) # assign new product
            logger.notifyChannel('ext assign', netsvc.LOG_INFO, "Successfully assigned product %s to product %s with type %s" %(parent_sku, child_sku, type))
        for child_sku in skus_to_update:
            conn.call('product_link.update', data + [child_sku, {'position': position.get(child_sku, 0), 'qty': quantities.get(child_sku, 1)}]) # update products already assigned
            logger.notifyChannel('ext assign', netsvc.LOG_INFO, "Successfully updated assignment of type %s of product %s to product %s" %(type, parent_sku, child_sku))
        return True

    #TODO move this code (get exportable image) and also some code in product_image.py and sale.py in base_sale_multichannel or in a new module in order to be more generic
    def get_exportable_images(self, cr, uid, ids, context=None):
        image_obj = self.pool.get('product.images')
        images_exportable_ids = image_obj.search(cr, uid, [('product_id', 'in', ids)], context=context)
        images_to_update_ids = image_obj.get_all_oeid_from_referential(cr, uid, context['external_referential_id'], context=None)
        images_to_create = [x for x in images_exportable_ids if not x in images_to_update_ids]

        if context.get('last_images_export_date', False):
            images_to_update_ids = image_obj.search(cr, uid, [('id', 'in', images_to_update_ids), '|', ('create_date', '>', context['last_images_export_date']), ('write_date', '>', context['last_images_export_date'])], context=context)
        return {'to_create' : images_to_create, 'to_update' : images_to_update_ids}

    def _mag_import_product_links_type(self, cr, uid, product, link_type, external_referential_id, conn, context=None):
        if context is None: context = {}
        logger = netsvc.Logger()
        product_link_obj = self.pool.get('product.link')
        selection_link_types = product_link_obj._columns['type'].selection(cr, uid, context)
        # This method could be completed to import grouped products too, you know, for Magento a product link is as
        # well a cross-sell, up-sell, related than the assignment between grouped products
        if link_type in [ltype[0] for ltype in selection_link_types]:
            product_links = []
            try:
                product_links = conn.call('product_link.list', [link_type, product.magento_sku])
            except Exception, e:
                self.log(cr, uid, product.id, "Error when retrieving the list of links in Magento for product with sku %s and product id %s !" % (product.magento_sku, product.id,))
                logger.notifyChannel('ext synchro', netsvc.LOG_DEBUG, "Error when retrieving the list of links in Magento for product with sku %s and product id %s !" % (product.magento_sku, product.id,))

            for product_link in product_links:
                ctx = context.copy()
                ctx['alternative_key'] = product_link['sku']
                linked_product_id = self.extid_to_oeid(cr, uid, product_link['product_id'], external_referential_id, context=context)
                link_data = {
                    'product_id': product.id,
                    'type': link_type,
                    'linked_product_id': linked_product_id,
                    'sequence': product_link['position'],
                }

                existing_link = product_link_obj.search(cr, uid,
                    [('product_id', '=', link_data['product_id']),
                     ('type', '=', link_data['type']),
                     ('linked_product_id', '=', link_data['linked_product_id'])
                    ], context=context)
                if existing_link:
                    product_link_obj.write(cr, uid, existing_link, link_data, context=context)
                else:
                    product_link_obj.create(cr, uid, link_data, context=context)
                logger.notifyChannel('Import Product Links', netsvc.LOG_INFO, "Successfully imported product link of type %s on product %s to product %s" %(link_type, product.id, linked_product_id))
        return True

    def mag_import_product_links_types(self, cr, uid, ids, link_types, external_referential_id, conn, context=None):
        if isinstance(ids, (int, long)): ids = [ids]
        for product in self.browse(cr, uid, ids, context=context):
            for link_type in link_types:
                self._mag_import_product_links_type(cr, uid, product, link_type, external_referential_id, conn, context=context)
        return True

    def mag_import_product_links(self, cr, uid, ids, external_referential_id, conn, context=None):
        link_types = self.pool.get('external.referential').get_magento_product_link_types(cr, uid, external_referential_id, conn, context=context)
        local_cr = pooler.get_db(cr.dbname).cursor()
        try:
            for product_id in ids:
                self.mag_import_product_links_types(local_cr, uid, [product_id], link_types, external_referential_id, conn, context=context)
                local_cr.commit()
        finally:
            local_cr.close()
        return True

product_product()
