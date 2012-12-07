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

import time
import unicodedata
import base64, urllib
import os
import xmlrpclib
from lxml import etree
import logging

from openerp.osv.orm import Model, setup_modifiers
from openerp.osv import fields
from openerp.osv.osv import except_osv
from openerp import pooler
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT

from .magerp_osv import MagerpModel
from base_external_referentials.decorator import only_for_referential, catch_error_in_report
from base_external_referentials.external_osv import ExternalSession

_logger = logging.getLogger(__name__)

#Enabling this to True will put all custom attributes into One page in
#the products view
GROUP_CUSTOM_ATTRS_TOGETHER = False


#TODO find a good method to replace all of the special caracter allowed by magento as name for product fields
special_character_to_replace = [
    (u"\xf8", u"diam"),
    (u'\xb5', u'micro'),
    (u'\xb2', u'2'),
    (u'\u0153', u'oe'),
    (u'\uff92', u'_'),
    (u'\ufffd', u'_'),
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

class magerp_product_category_attribute_options(MagerpModel):
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


class product_category(MagerpModel):
    _inherit = "product.category"

    def _merge_with_default_values(self, cr, uid, external_session, ressource, vals, sub_mapping_list, defaults=None, context=None):
        vals = super(product_category, self)._merge_with_default_values(cr, uid, external_session, ressource, vals, sub_mapping_list, defaults=defaults, context=context)
        #some time magento category doesn't have a name
        if not vals.get('name'):
            vals['name'] = 'Undefined'
        return vals

    def _get_default_export_values(self, *args, **kwargs):
        defaults = super(product_category, self)._get_default_export_values(*args, **kwargs)
        if defaults == None: defaults={}
        defaults.update({'magento_exportable': True})
        return defaults

    def multi_lang_read(self, cr, uid, external_session, ids, fields_to_read, langs, resources=None, use_multi_lang = True, context=None):
        return super(product_category, self).multi_lang_read(cr, uid, external_session, ids, fields_to_read, langs,
                                                            resources=resources,
                                                            use_multi_lang = False,
                                                            context=context)

    def ext_create(self, cr, uid, external_session, resources, mapping=None, mapping_id=None, context=None):
        ext_create_ids={}
        storeview_to_lang = context['storeview_to_lang']
        main_lang = context['main_lang']
        for resource_id, resource in resources.items():
            #Move this part of code in a python lib
            parent_id = resource[main_lang]['parent_id']
            del resource[main_lang]['parent_id']
            ext_id = external_session.connection.call('catalog_category.create', [parent_id, resource[main_lang]])
            for storeview, lang in storeview_to_lang.items():
                external_session.connection.call('catalog_category.update', [ext_id, resource[lang], storeview])
            ext_create_ids[resource_id] = ext_id
        return ext_create_ids


    def ext_update(self, cr, uid, external_session, resources, mapping=None, mapping_id=None, context=None):
        ext_update_ids={}
        storeview_to_lang = context['storeview_to_lang']
        main_lang = context['main_lang']
        for resource_id, resource in resources.items():
            #Move this part of code in a python lib
            ext_id = resource[main_lang]['ext_id']
            del resource[main_lang]['ext_id']
            parent_id = resource[main_lang]['parent_id']
            del resource[main_lang]['parent_id']
            external_session.connection.call('catalog_category.update', [ext_id, resource[main_lang], False])
            external_session.connection.call('oerp_catalog_category.move', [ext_id, parent_id])
            for storeview, lang in storeview_to_lang.items():
                del resource[lang]['ext_id']
                external_session.connection.call('catalog_category.update', [ext_id, resource[lang], storeview])
            ext_update_ids[resource_id] = ext_id
        return ext_update_ids

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
        'url_key': fields.char('URL-key', size=100), #Readonly
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

    def _get_external_resource_ids(self, cr, uid, external_session, resource_filter=None, mapping=None, context=None):
        def get_child_ids(tree):
            result=[]
            result.append(tree['category_id'])
            for categ in tree['children']:
                result += get_child_ids(categ)
            return result
        ids=[]
        confirmation = external_session.connection.call('catalog_category.currentStore', [0])   #Set browse to root store
        if confirmation:
            categ_tree = external_session.connection.call('catalog_category.tree')             #Get the tree
            ids = get_child_ids(categ_tree)
        return ids


class magerp_product_attributes(MagerpModel):
    _name = "magerp.product_attributes"
    _description = "Attributes of products"
    _rec_name = "attribute_code"

    def _get_group(self, cr, uid, ids, prop, unknow_none, context=None):
        res = {}
        for attribute in self.browse(cr, uid, ids, context):
            res[attribute.id] = self.pool.get('magerp.product_attribute_groups').extid_to_existing_oeid(cr, uid, attribute.group_id, attribute.referential_id.id)
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
                                           ('weight', 'Weight'),
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

    _defaults = {'based_on': lambda*a: 'product_template',
                 }
    #mapping magentofield:(openerpfield,typecast,)
    #have an entry for each mapped field
    _no_create_list = ['product_id',
                       'name',
                       'description',
                       'short_description',
                       'sku',
                       'weight',
                       'category_ids',
                       'price',
                       'cost',
                       'set',
                       'ean',
                       ]
    _translatable_default_codes = ['description',
                                   'meta_description',
                                   'meta_keyword',
                                   'meta_title',
                                   'name',
                                   'short_description',
                                   'url_key',
                                   ]
    _not_store_in_json = ['minimal_price',
                          'special_price',
                          'description',
                          'meta_description',
                          'meta_keyword',
                          'meta_title',
                          'name',
                          'short_description',
                          'url_key',
                          ]
    _type_conversion = {'':'char',
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
    _type_casts = {'':'unicode',
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
    _variant_fields = ['color',
                       'dimension',
                       'visibility',
                       'special_price',
                       'special_price_from_date',
                       'special_price_to_date',
                       ]


    #For some field you can specify the syncronisation way
    #in : Magento => OpenERP
    #out : Magento <= OpenERP
    #in_out (default_value) : Magento <=> OpenERP
    _sync_way = {'has_options' : 'in',
                 'tier_price': 'in',
               }

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
        if referential_id:
            for id in ids:
                all_vals = self.read(cr, uid, id, [], context)

                #Fetch Options
                if 'frontend_input' in all_vals.keys() and all_vals['frontend_input'] in ['select', 'multiselect']:
                    core_imp_conn = self.pool.get('external.referential').external_connection(cr, uid, [referential_id])
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
                    core_imp_conn = self.pool.get('external.referential').external_connection(cr, uid, vals['referential_id'])
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

    def _default_mapping(self, cr, uid, ttype, field_name, vals, attribute_id, model_id, mapping_line, referential_id):
        #TODO refactor me and use the direct mapping
        #If the field have restriction on domain
        #Maybe we can give the posibility to map directly m2m and m2o field_description
        #by filtrering directly with the domain and the string value
        if ttype in ['char', 'text', 'date', 'float', 'weee', 'boolean']:
            mapping_line['evaluation_type'] = 'direct'
            if ttype == 'float':
                mapping_line['external_type'] = 'float'
            elif ttype == 'boolean':
                mapping_line['external_type'] = 'int'
            else:
                mapping_line['external_type'] = 'unicode'

        elif ttype in ['many2one']:
            mapping_line['evaluation_type'] = 'function'
            mapping_line['in_function'] = \
               ("if '%(attribute_code)s' in resource:\n"
                "    option_id = self.pool.get('magerp.product_attribute_options').search(cr, uid, [('attribute_id','=',%(attribute_id)s),('value','=',ifield)])\n"
                "    if option_id:\n"
                "        result = [('%(field_name)s', option_id[0])]")  % ({'attribute_code': vals['attribute_code'], 'attribute_id': attribute_id, 'field_name': field_name})
            # we browse on resource['%(field_name)s'][0] because resource[field_name] is in the form (id, name)
            mapping_line['out_function'] = \
               ("if '%(field_name)s' in resource:\n"
                "    result = [('%(attribute_code)s', False)]\n"
                "    if resource.get('%(field_name)s'):\n"
                "        option = self.pool.get('magerp.product_attribute_options').browse(cr, uid, resource['%(field_name)s'][0])\n"
                "        if option:\n"
                "            result = [('%(attribute_code)s', option.value)]") % ({'field_name': field_name, 'attribute_code': vals['attribute_code']})
        elif ttype in ['many2many']:
            mapping_line['evaluation_type'] = 'function'
            mapping_line['in_function'] = ("option_ids = []\n"
                "opt_obj = self.pool.get('magerp.product_attribute_options')\n"
                "for ext_option_id in ifield:\n"
                "    option_ids.extend(opt_obj.search(cr, uid, [('attribute_id','=',%(attribute_id)s), ('value','=',ext_option_id)]))\n"
                "result = [('%(field_name)s', [(6, 0, option_ids)])]") % ({'attribute_id': attribute_id, 'field_name': field_name})
            mapping_line['out_function'] = ("result=[('%(attribute_code)s', [])]\n"
                "if resource.get('%(field_name)s'):\n"
                "    options = self.pool.get('magerp.product_attribute_options').browse(cr, uid, resource['%(field_name)s'])\n"
                "    result = [('%(attribute_code)s', [option.value for option in options])]") % \
               ({'field_name': field_name, 'attribute_code': vals['attribute_code']})
        elif ttype in ['binary']:
            warning_text = "Binary mapping is actually not supported (attribute: %s)" % (vals['attribute_code'],)
            _logger.warn(warning_text)
            warning_msg = ("import logging\n"
                           "logger = logging.getLogger('in/out_function')\n"
                           "logger.warn('%s')") % (warning_text,)
            mapping_line['in_function'] = mapping_line['out_function'] = warning_msg
        return mapping_line

    def _create_mapping(self, cr, uid, ttype, field_id, field_name, referential_id, model_id, vals, attribute_id):
        """Search & create mapping entries"""
        if vals['attribute_code'] in self._no_create_list:
            return False
        mapping_id = self.pool.get('external.mapping').search(cr, uid, [('referential_id', '=', referential_id), ('model_id', '=', model_id)])
        if mapping_id:
            existing_line = self.pool.get('external.mapping.line').search(cr, uid, [('external_field', '=', vals['attribute_code']), ('mapping_id', '=', mapping_id[0])])
            if not existing_line:
                mapping_line = {'external_field': vals['attribute_code'],
                                'sequence': 0,
                                'mapping_id': mapping_id[0],
                                'type': self._sync_way.get(vals['attribute_code'], 'in_out'),
                                'external_type': self._type_casts[vals.get('frontend_input', False)],
                                'field_id': field_id, }
                mapping_line = self._default_mapping(cr, uid, ttype, field_name, vals, attribute_id, model_id, mapping_line, referential_id)
                self.pool.get('external.mapping.line').create(cr, uid, mapping_line)
        return True


"""Dont remove the code, we might need it --sharoon
class magerp_product_attributes_set_info(Model):
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

class magerp_product_attribute_options(MagerpModel):
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
                value = unicode(vals['value'])
                #Fixme: What to do when Magento offers emty options which open erp doesnt?
                #Such cases dictionary is: {'value':'','label':''}
                if update:
                    existing_ids = self.search(
                        cr, uid,
                        [('attribute_id', '=', context['attribute_id']),
                         ('value', '=', value)],
                        context=context)
                    if len(existing_ids) == 1:
                        to_remove_ids.remove(existing_ids[0])
                        self.write(cr, uid, existing_ids[0], {'label': vals.get('label', False)})
                        continue

                self.create(cr, uid, {
                                        'attribute_id': context['attribute_id'],
                                        'value': value,
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


class magerp_product_attribute_set(MagerpModel):
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


    def update_attribute(self, cr, uid, ids, context=None):
        ref_obj = self.pool.get('external.referential')
        mag_ref_ids = ref_obj.search(cr, uid, [('version_id','ilike', 'magento')], context=context)
        for referential in ref_obj.browse(cr, uid, mag_ref_ids, context=context):
            external_session = ExternalSession(referential, referential)
            for attr_set_id in ids:
                attr_set_ext_id = self.get_extid(cr, uid, attr_set_id, referential.id, context=context)
                if attr_set_ext_id:
                    self._import_attribute(cr, uid, external_session, attr_set_ext_id, context=context)
                    self._import_attribute_relation(cr, uid, external_session, [attr_set_ext_id], context=context)
        return True

    #TODO refactor me
    def _import_attribute(self, cr, uid, external_session, attr_set_ext_id, attributes_imported=None, context=None):
        attr_obj = self.pool.get('magerp.product_attributes')
        mage_inp = external_session.connection.call('ol_catalog_product_attribute.list', [attr_set_ext_id])             #Get the tree
        mapping = {'magerp.product_attributes' : attr_obj._get_mapping(cr, uid, external_session.referential_id.id, context=context)}
        attribut_to_import = []
        if not attributes_imported: attributes_imported=[]
        for attribut in mage_inp:
            ext_id = attribut['attribute_id']
            if not ext_id in attributes_imported:
                attributes_imported.append(ext_id)
                attr_obj._record_one_external_resource(cr, uid, external_session, attribut,
                                                defaults={'referential_id':external_session.referential_id.id},
                                                mapping=mapping,
                                                context=context,
                                            )
        external_session.logger.info("All attributs for the attributs set id %s was succesfully imported", attr_set_ext_id)
        return True

    #TODO refactor me
    def _import_attribute_relation(self, cr, uid, external_session, attr_set_ext_ids, context=None):
        #Relate attribute sets & attributes
        mage_inp = {}
        #Pass in {attribute_set_id:{attributes},attribute_set_id2:{attributes}}
        #print "Attribute sets are:", attrib_sets
        #TODO find a solution in order to import the relation in a incremental way (maybe splitting this function in two)
        for attr_id in attr_set_ext_ids:
            mage_inp[attr_id] = external_session.connection.call('ol_catalog_product_attribute.relations', [attr_id])
        if mage_inp:
            self.relate(cr, uid, mage_inp, external_session.referential_id.id, context)
        return True

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


class magerp_product_attribute_groups(MagerpModel):
    _name = "magerp.product_attribute_groups"
    _description = "Attribute groups in Magento"
    _rec_name = 'attribute_group_name'
    _order = "sort_order"
    def _get_set(self, cr, uid, ids, prop, unknow_none, context=None):
        res = {}
        for attribute_group in self.browse(cr, uid, ids, context):
            res[attribute_group.id] = self.pool.get('magerp.product_attribute_set').extid_to_oeid(cr, uid, attribute_group.attribute_set_id, attribute_group.referential_id.id)
        return res

    def _get_filter(self, cr, uid, external_session, step, previous_filter=None, context=None):
        attrset_ids = self.pool.get('magerp.product_attribute_set').get_all_extid_from_referential(cr, uid, external_session.referential_id.id, context=context)
        return {'attribute_set_id':{'in':attrset_ids}}

    _columns = {
        'attribute_set_id':fields.integer('Attribute Set ID'),
        'attribute_set':fields.function(_get_set, type="many2one", relation="magerp.product_attribute_set", method=True, string="Attribute Set"),
        'attribute_group_name':fields.char('Group Name', size=100),
        'sort_order':fields.integer('Sort Order'),
        'default_id':fields.integer('Default'),
        'referential_id':fields.many2one('external.referential', 'Magento Instance', readonly=True),
        }

class product_tierprice(Model):
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

class product_product_type(Model):
    _name = 'magerp.product_product_type'
    _columns = {
        'name': fields.char('Name', size=100, required=True, translate=True),
        'product_type': fields.char('Type', size=100, required=True, help="Use the same name of Magento product type, for example 'simple'."),
        'default_type': fields.selection([('product','Stockable Product'),('consu', 'Consumable'),('service','Service')], 'Default Product Type', required=True, help="Default product's type (Procurement) when a product is imported from Magento."),
        }


class product_mag_osv(MagerpModel):
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
            raise except_osv(_('User Error'), _('Please chose an attribute set before'))

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

    def redefine_prod_view(self, cr, uid, field_names, context=None):
        """
        Rebuild the product view with attribute groups and attributes
        """
        if context is None: context = {}
        attr_set_obj = self.pool.get('magerp.product_attribute_set')
        attr_group_obj = self.pool.get('magerp.product_attribute_groups')
        attr_obj = self.pool.get('magerp.product_attributes')
        translation_obj = self.pool.get('ir.translation')

        attribute_set_id = context['set']
        attr_set = attr_set_obj.browse(cr, uid, attribute_set_id)
        attr_group_fields_rel = {}

        multiwebsites = context.get('multiwebsite', False)

        fields_get = self.fields_get(cr, uid, field_names, context)

        cr.execute("select attr_id, group_id, attribute_code, frontend_input, "
                   "frontend_label, is_required, apply_to, field_name "
                   "from magerp_attrset_attr_rel "
                   "left join magerp_product_attributes "
                   "on magerp_product_attributes.id = attr_id "
                   "where magerp_attrset_attr_rel.set_id=%s" %
                   attribute_set_id)

        results = cr.dictfetchall()
        attribute = results.pop()
        while results:
            mag_group_id = attribute['group_id']
            oerp_group_id = attr_group_obj.extid_to_existing_oeid(
                cr, uid, attr_set.referential_id.id, mag_group_id)
            # FIXME: workaround in multi-Magento instances (databases)
            # where attribute group might not be found due to the way we
            # share attributes currently
            if not oerp_group_id:
                ref_ids = self.pool.get(
                    'external.referential').search(cr, uid, [])
                for ref_id in ref_ids:
                     if ref_id != attr_set.referential_id.id:
                         oerp_group_id = attr_group_obj.extid_to_existing_oeid(
                             cr, uid, ref_id, mag_group_id)
                         if oerp_group_id:
                             break

            group_name = attr_group_obj.read(
                cr, uid, oerp_group_id,
                ['attribute_group_name'],
                context=context)['attribute_group_name']

            # Create a page for each attribute group
            attr_group_fields_rel.setdefault(group_name, [])
            while True:
                if attribute['group_id'] != mag_group_id:
                    break

                if attribute['field_name'] in field_names:
                    if not attribute['attribute_code'] in attr_obj._no_create_list:
                        if (group_name in  ['Meta Information',
                                            'General',
                                            'Custom Layout Update',
                                            'Prices',
                                            'Design']) or \
                           GROUP_CUSTOM_ATTRS_TOGETHER==False:
                            attr_group_fields_rel[group_name].append(attribute)
                        else:
                            attr_group_fields_rel.setdefault(
                                'Custom Attributes', []).append(attribute)
                if results:
                    attribute = results.pop()
                else:
                    break

        notebook = etree.Element('notebook', colspan="4")

        attribute_groups = attr_group_fields_rel.keys()
        attribute_groups.sort()
        for group in attribute_groups:
            lang = context.get('lang', '')
            trans = translation_obj._get_source(
                cr, uid, 'product.product', 'view', lang, group)
            trans = trans or group
            if attr_group_fields_rel.get(group):
                page = etree.SubElement(notebook, 'page', string=trans)
                for attribute in attr_group_fields_rel.get(group, []):
                    if attribute['frontend_input'] == 'textarea':
                        etree.SubElement(page, 'newline')
                        etree.SubElement(
                            page,
                            'separator',
                            colspan="4",
                            string=fields_get[attribute['field_name']]['string'])

                    f = etree.SubElement(
                        page, 'field', name=attribute['field_name'])

                    # apply_to is a string like
                    # "simple,configurable,virtual,bundle,downloadable"
                    req_apply_to = not attribute['apply_to'] or \
                        'simple' in attribute['apply_to'] or \
                        'configurable' in attribute['apply_to']
                    if attribute['is_required'] and \
                       req_apply_to and \
                        attribute['attribute_code'] not in self._magento_fake_mandatory_attrs:
                        f.set('attrs', "{'required': [('magento_exportable', '=', True)]}")

                    if attribute['frontend_input'] == 'textarea':
                        f.set('nolabel', "1")
                        f.set('colspan', "4")

                    setup_modifiers(f, fields_get[attribute['field_name']],
                                    context=context)

        if multiwebsites:
            website_page = etree.SubElement(
                notebook, 'page', string=_('Websites'))
            wf = etree.SubElement(
                website_page, 'field', name='websites_ids', nolabel="1")
            setup_modifiers(wf, fields_get['websites_ids'], context=context)

        return notebook

    def _filter_fields_to_return(self, cr, uid, field_names, context=None):
        '''This function is a hook in order to filter the fields that appears on the view'''
        return field_names

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if context is None:
            context = {}
        result = super(product_mag_osv, self).fields_view_get(
            cr, uid, view_id,view_type,context,toolbar=toolbar)
        if view_type == 'form':
            eview = etree.fromstring(result['arch'])
            btn = eview.xpath("//button[@name='open_magento_fields']")
            if btn:
                btn = btn[0]
            page_placeholder = eview.xpath(
                "//page[@string='attributes_placeholder']")

            attrs_mag_notebook = "{'invisible': [('set', '=', False)]}"

            if context.get('set'):
                fields_obj = self.pool.get('ir.model.fields')
                models = ['product.template']
                if self._name == 'product.product':
                    models.append('product.product')

                model_ids = self.pool.get('ir.model').search(
                    cr, uid, [('model', 'in', models)], context=context)
                field_ids = fields_obj.search(
                    cr, uid,
                    [('model_id', 'in', model_ids)],
                    context=context)
                #TODO it will be better to avoid adding fields here
                #Moreover we should also add the field mag_manage_stock
                field_names = ['product_type']
                fields = fields_obj.browse(cr, uid, field_ids, context=context)
                for field in fields:
                    if field.name.startswith('x_'):
                        field_names.append(field.name)
                website_ids = self.pool.get('external.shop.group').search(
                    cr, uid,
                    [('referential_type', '=ilike', 'mag%')],
                    context=context)
                if len(website_ids) > 1:
                    context['multiwebsite'] = True
                    field_names.append('websites_ids')

                field_names = self._filter_fields_to_return(
                    cr, uid, field_names, context)
                result['fields'].update(
                    self.fields_get(cr, uid, field_names, context))

                attributes_notebook = self.redefine_prod_view(
                                    cr, uid, field_names, context)

                # if the placeholder is a "page", that means we are
                # in the product main form. If it is a "separator", it
                # means we are in the attributes popup
                if page_placeholder:
                    placeholder = page_placeholder[0]
                    magento_page = etree.Element(
                        'page',
                        string=_('Magento Information'),
                        attrs=attrs_mag_notebook)
                    setup_modifiers(magento_page, context=context)
                    f = etree.SubElement(
                        magento_page,
                        'field',
                        name='product_type',
                        attrs="{'required': [('magento_exportable', '=', True)]}")
                    setup_modifiers(f, field=result['fields']['product_type'], context=context)
                    magento_page.append(attributes_notebook)
                    btn.getparent().remove(btn)
                else:
                    placeholder = eview.xpath(
                        "//separator[@string='attributes_placeholder']")[0]
                    magento_page = attributes_notebook

                placeholder.getparent().replace(placeholder, magento_page)
            elif btn != []:
                new_btn = etree.Element(
                    'button',
                    name='open_magento_fields',
                    string=_('Open Magento Fields'),
                    icon='gtk-go-forward',
                    type='object',
                    colspan='2',
                    attrs=attrs_mag_notebook)
                setup_modifiers(new_btn, context=context)
                btn.getparent().replace(btn, new_btn)
                if page_placeholder:
                    placeholder = page_placeholder[0]
                    placeholder.getparent().remove(placeholder)

            result['arch'] = etree.tostring(eview, pretty_print=True)
            #TODO understand (and fix) why the orm fill the field size for the text field :S
            for field in result['fields']:
                if result['fields'][field]['type'] == 'text':
                    if 'size' in result['fields'][field]: del result['fields'][field]['size']
        return result

class product_template(product_mag_osv):
    _inherit = "product.template"
    _columns = {
        'magerp_tmpl' : fields.serialized('Magento Template Fields'),
        'set':fields.many2one('magerp.product_attribute_set', 'Attribute Set'),
        'websites_ids': fields.many2many('external.shop.group', 'magerp_product_shop_group_rel', 'product_id', 'shop_group_id', 'Websites', help='By defaut product will be exported on every website, if you want to export it only on some website select them here'),
        'mag_manage_stock': fields.selection([
                                ('use_default','Use Default Config'),
                                ('no', 'Do Not Manage Stock'),
                                ('yes','Manage Stock')],
                                'Manage Stock Level'),
        'mag_manage_stock_shortage': fields.selection([
                                ('use_default','Use Default Config'),
                                ('no', 'No Sell'),
                                ('yes','Sell qty < 0'),
                                ('yes-and-notification','Sell qty < 0 and Use Customer Notification')],
                                'Manage Inventory Shortage'),
        }

    _defaults = {
        'mag_manage_stock': 'use_default',
        'mag_manage_stock_shortage': 'use_default',
        }


class product_product(product_mag_osv):
    _inherit = "product.product"

    def send_to_external(self, cr, uid, external_session, resources, mapping, mapping_id, update_date=None, context=None):
        product_ids = resources.keys()
        res = super(product_product, self).send_to_external(cr, uid, external_session, resources, mapping, mapping_id, update_date=update_date, context=context)
        if context.get('export_product') != 'link':
            self.export_inventory(cr, uid, external_session, product_ids, context=context)
        return res

    def map_and_update_product(self, cr, uid, external_session, resource, sku, context=None):
        res = external_session.connection.call('catalog_product.info', [sku, False, False, 'sku'])
        ext_id = res['product_id']
        external_session.connection.call('ol_catalog_product.update', [ext_id, resource, False, 'id'])
        return ext_id

    @only_for_referential('magento')
    def _get_external_resources(self, cr, uid, external_session, external_id=None, resource_filter=None,
                                         mapping=None, mapping_id=None, fields=None, context=None):
        if external_id:
            return external_session.connection.call('catalog_product.info', [external_id, False, False, 'id'])
        else:
            return super(product_product, self)._get_external_resources(cr, uid, external_session,
                                                                    external_id=external_id,
                                                                    resource_filter=resource_filter,
                                                                    mapping=mapping,
                                                                    mapping_id=mapping_id,
                                                                    fields=fields,
                                                                    context=context)


    #TODO reimplement the grouped product
    def ext_create(self, cr, uid, external_session, resources, mapping=None, mapping_id=None, context=None):
        ext_create_ids={}
        storeview_to_lang = context['storeview_to_lang']
        main_lang = context['main_lang']
        for resource_id, resource in resources.items():
            #Move this part of code in a python lib
            product_type = resource[main_lang]['type_id']
            attr_set = resource[main_lang]['set']
            sku = resource[main_lang]['sku']
            del resource[main_lang]['type_id']
            del resource[main_lang]['set']
            del resource[main_lang]['sku']
            try:
                ext_id = external_session.connection.call('ol_catalog_product.create', [product_type, attr_set, sku, resource[main_lang]])
            except xmlrpclib.Fault, e:
                if e.faultCode == 1:
                    # a product with same SKU exists on Magento, we rebind it
                    #TODO fix magento API. Indeed catalog_product.info seem to be broken
                    try:
                        ext_id = self.map_and_update_product(cr, uid, external_session, resource[main_lang], sku, context=context)
                    except:
                        raise except_osv(_('Error!'), _("Product %s already exist in Magento. Failed to rebind it. Please do it manually")%(sku))
                else:
                    raise

            for storeview, lang in storeview_to_lang.items():
                external_session.connection.call('ol_catalog_product.update', [ext_id, resource[lang], storeview, 'id'])
            ext_create_ids[resource_id] = ext_id
        return ext_create_ids

    def ext_update(self, cr, uid, external_session, resources, mapping=None, mapping_id=None, context=None):
        if context.get('export_product') == 'link':
            return self.ext_update_link_data(cr, uid, external_session, resources, mapping=mapping,
                                                            mapping_id=mapping_id, context=context)
        else:
            ext_update_ids={}
            storeview_to_lang = context['storeview_to_lang']
            main_lang = context['main_lang']
            for resource_id, resource in resources.items():
                #Move this part of code in a python lib
                ext_id = resource[main_lang]['ext_id']
                del resource[main_lang]['ext_id']
                external_session.connection.call('ol_catalog_product.update', [ext_id, resource[main_lang], False, 'id'])
                for storeview, lang in storeview_to_lang.items():
                    del resource[lang]['ext_id']
                    external_session.connection.call('ol_catalog_product.update', [ext_id, resource[lang], storeview, 'id'])
                ext_update_ids[resource_id] = ext_id
            return ext_update_ids

    @only_for_referential('magento')
    def _check_if_export(self, cr, uid, external_session, product, context=None):
        if context.get('export_product') == 'simple' and product.product_type == 'simple':
            return True
        elif context.get('export_product') == 'special' and product.product_type != 'simple':
            return True
        elif context.get('export_product') == 'link':
            return True
        return False

    #TODO make me generic when image export will be refactor
    def export_product_images(self, cr, uid, external_session, ids, context=None):
        image_obj = self.pool.get('product.images')
        for product in self.browse(cr, uid, ids, context=context):
            image_ids = [image.id for image in product.image_ids]
            external_session.logger.info('export %s images for product %s'%(len(image_ids), product.name))
            image_obj.update_remote_images(cr, uid, external_session, image_ids, context=context)
        return True


    #TODO base the import on the mapping and the function ext_import
    def import_product_image(self, cr, uid, id, referential_id, conn, ext_id=None, context=None):
        image_obj = self.pool.get('product.images')
        if not ext_id:
            ext_id = self.get_extid(cr, uid, id, referential_id, context=context)
        # TODO everythere will should pass the params 'id' for magento api in order to force
        # to use the id as external key instead of mixed id/sku
        img_list = conn.call('catalog_product_attribute_media.list', [ext_id, False, 'id'])
        _logger.info("Magento image for product ext_id %s: %s", ext_id, img_list)
        images_name = []
        for image in img_list:
            img=False
            try:
                (filename, header) = urllib.urlretrieve(image['url'])
                f = open(filename , 'rb')
                data = f.read()
                f.close()
                if "DOCTYPE html PUBLIC" in data:
                    _logger.warn("failed to open the image %s from Magento", image['url'])
                    continue
                else:
                    img = base64.encodestring(data)
            except Exception, e:
                #TODO raise correctly the error
                _logger.error("failed to open the image %s from Magento, error : %s", image['url'], e, exc_info=True)
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

    def get_field_to_export(self, cr, uid, ids, mapping, mapping_id, context=None):
        res = super(product_product, self).get_field_to_export(cr, uid, ids, mapping, mapping_id, context=context)
        if 'product_image' in res: res.remove('product_image')
        if context.get('attribut_set_id'):
            #When OpenERP will be clean, maybe we can add some cache here (@ormcache)
            #But for now the bottle of neck is the read the computed fields
            #So no need to do it for now
            attr_set = self.pool.get('magerp.product_attribute_set').browse(cr, uid, \
                                                context['attribut_set_id'], context=context)
            magento_field = [attribut['field_name'] for attribut in attr_set.attributes]
            return [field for field in res if (field[0:9] != "x_magerp_" or field in magento_field)]
        else:
            return res

    def _get_oe_resources(self, cr, uid, external_session, ids, langs, smart_export=None,
                            last_exported_date=None, mapping=None, mapping_id=None, context=None):
        resources={}
        set_to_product_ids = {}
        for product in self.browse(cr, uid, ids, context=context):
            if not set_to_product_ids.get(product.set.id):
                set_to_product_ids[product.set.id] = [product.id]
            else:
                set_to_product_ids[product.set.id].append(product.id)
        for attribut_id, product_ids in set_to_product_ids.iteritems():
            context['attribut_set_id'] = attribut_id
            resources.update(super(product_product, self)._get_oe_resources(
                                                cr, uid, external_session, product_ids, langs,
                                                smart_export=smart_export,
                                                last_exported_date=last_exported_date,
                                                mapping=mapping,
                                                mapping_id=mapping_id,
                                                context=context
                                                ))
        return resources

    def _product_type_get(self, cr, uid, context=None):
        ids = self.pool.get('magerp.product_product_type').search(cr, uid, [], order='id')
        product_types = self.pool.get('magerp.product_product_type').read(cr, uid, ids, ['product_type','name'], context=context)
        return [(pt['product_type'], pt['name']) for pt in product_types]

    def _is_magento_exported(self, cr, uid, ids, field_name, arg, context=None):
        """Return True if the product is already exported to at least one magento shop
        """
        res = {}
        # get all magento external_referentials
        referential_ids = self.pool.get('external.referential').search(cr, uid, [('magento_referential', '=', True)])
        for product_id in ids:
            for referential_id in referential_ids:
                res[product_id] = False
                if self.get_extid(cr, uid, product_id, referential_id, context):
                    res[product_id] = True
                    break
        return res

    _columns = {
        'magerp_variant' : fields.serialized('Magento Variant Fields'),
        'magento_exportable':fields.boolean('Exported to Magento?'),
        'created_at':fields.date('Created'), #created_at & updated_at in magento side, to allow filtering/search inside OpenERP!
        'updated_at':fields.date('Created'),
        'tier_price':fields.one2many('product.tierprice', 'product', 'Tier Price'),
        'product_type': fields.selection(_product_type_get, 'Magento Product Type'),
        'magento_exported': fields.function(_is_magento_exported, type="boolean", method=True, string="Exists on Magento"),  # used to set the sku readonly when already exported
        }

    _defaults = {
        'magento_exportable': True,
        'product_type': 'simple',
    }

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
            if shop.referential_id and shop.referential_id.type_id.name == 'Magento':
                for product_id in ids:
                    mgn_product = self.get_extid(cr, uid, product_id, shop.referential_id.id)
                    if mgn_product:
                        not_delete = True
                        break
        if not_delete:
            if len(ids) > 1:
                raise except_osv(_('Warning!'),
                                 _('They are some products related to Magento. '
                                   'They can not be deleted!\n'
                                   'You can change their Magento status to "Disabled" '
                                   'and uncheck the active box to hide them from OpenERP.'))
            else:
                raise except_osv(_('Warning!'),
                                 _('This product is related to Magento. '
                                   'It can not be deleted!\n'
                                   'You can change it Magento status to "Disabled" '
                                   'and uncheck the active box to hide it from OpenERP.'))
        else:
            return super(product_product, self).unlink(cr, uid, ids, context)

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
        map_shortage = {
            "use_default": 0,
            "no": 0,
            "yes": 1,
            "yes-and-notification": 2,
        }

        stock_field = (shop.product_stock_field_id and
                       shop.product_stock_field_id.name or
                       'virtual_available')
        stock_quantity = product[stock_field]
        
        return {'qty': stock_quantity,
                'manage_stock': int(product.mag_manage_stock == 'yes'),
                'use_config_manage_stock': int(product.mag_manage_stock == 'use_default'),
                'backorders': map_shortage[product.mag_manage_stock_shortage],
                'use_config_backorders':int(product.mag_manage_stock_shortage == 'use_default'),
                # put the stock availability to "out of stock"
                'is_in_stock': int(stock_quantity > 0)}

    def export_inventory(self, cr, uid, external_session, ids, context=None):
        """
        Export to Magento the stock quantity for the products in ids which
        are already exported on Magento and are not service products.

        :param int shop_id: id of the shop where the stock inventory has
        to be exported
        :param Connection connection: connection object
        :return: True
        """
        #TODO get also the list of product which the option mag_manage_stock have changed
        #This can be base on the group_fields that can try tle last write date of a group of fields
        if context is None: context = {}

        # use the stock location defined on the sale shop
        # to compute the stock value
        stock = external_session.sync_from_object.warehouse_id.lot_stock_id
        location_ctx = context.copy()
        location_ctx['location'] = stock.id
        for product_id in ids:
            self._export_inventory(cr, uid, external_session, product_id, context=location_ctx)

        return True

    @catch_error_in_report
    def _export_inventory(self, cr, uid, external_session, product_id, context=None):
        product = self.browse(cr, uid, product_id, context=context)
        stock = external_session.sync_from_object.warehouse_id.lot_stock_id
        mag_product_id = self.get_extid(
            cr, uid, product.id, external_session.referential_id.id, context=context)
        if not mag_product_id:
            return False  # skip products which are not exported
        inventory_vals = self._prepare_inventory_magento_vals(
            cr, uid, product, stock, external_session.sync_from_object, context=context)

        external_session.connection.call('oerp_cataloginventory_stock_item.update',
                        [mag_product_id, inventory_vals])

        external_session.logger.info(
            "Successfully updated stock level at %s for "
            "product with code %s " %
            (inventory_vals['qty'], product.default_code))
        return True

    #TODO change the magento api to be able to change the link direct from the function
    # ol_catalog_product.update
    def ext_update_link_data(self, cr, uid, external_session, resources, mapping=None, mapping_id=None, context=None):
        for resource_id, resource in resources.items():
            for type_selection in self.pool.get('product.link').get_link_type_selection(cr, uid, context):
                link_type = type_selection[0]
                position = {}
                linked_product_ids = []
                for link in resource[context['main_lang']].get('product_link', []):
                    if link['type'] == link_type:
                        if link['is_active']:
                            linked_product_ids.append(link['link_product_id'])
                            position[link['link_product_id']] = link['position']
                self.ext_product_assign(cr, uid, external_session, link_type, resource[context['main_lang']]['ext_id'],
                                            linked_product_ids, position=position, context=context)
        return True

    def ext_product_assign(self, cr, uid, external_session, link_type, ext_parent_id, ext_child_ids,
                                                    quantities=None, position=None, context=None):
        context = context or {}
        position = position or {}
        quantities = quantities or {}


        #Patch for magento api prototype
        #for now the method for goodies is freeproduct
        #It will be renammed soon and so this patch will be remove too
        if link_type == 'goodies': link_type= 'freeproduct'
        #END PATCH

        magento_args = [link_type, ext_parent_id]
        # magento existing children ids
        child_list = external_session.connection.call('product_link.list', magento_args)
        old_child_ext_ids = [x['product_id'] for x in child_list]

        ext_id_to_remove = []
        ext_id_to_assign = []
        ext_id_to_update = []

        # compute the diff between openerp and magento
        for c_ext_id in old_child_ext_ids:
            if c_ext_id not in ext_child_ids:
                ext_id_to_remove.append(c_ext_id)
        for c_ext_id in ext_child_ids:
            if c_ext_id in old_child_ext_ids:
                ext_id_to_update.append(c_ext_id)
            else:
                ext_id_to_assign.append(c_ext_id)

        # calls to magento to delete, create or update the links
        for c_ext_id in ext_id_to_remove:
             # remove the product links that are no more setup on openerp
            external_session.connection.call('product_link.remove', magento_args + [c_ext_id])
            external_session.logger.info(("Successfully removed assignment of type %s for"
                                 "product %s to product %s") % (link_type, ext_parent_id, c_ext_id))
        for c_ext_id in ext_id_to_assign:
            # assign new product links
            external_session.connection.call('product_link.assign',
                      magento_args +
                      [c_ext_id,
                          {'position': position.get(c_ext_id, 0),
                           'qty': quantities.get(c_ext_id, 1)}])
            external_session.logger.info(("Successfully assigned product %s to product %s"
                                            "with type %s") %(link_type, ext_parent_id, c_ext_id))
        for child_ext_id in ext_id_to_update:
            # update products links already assigned
            external_session.connection.call('product_link.update',
                      magento_args +
                      [c_ext_id,
                          {'position': position.get(c_ext_id, 0),
                           'qty': quantities.get(c_ext_id, 1)}])
            external_session.logger.info(("Successfully updated assignment of type %s of"
                                 "product %s to product %s") %(link_type, ext_parent_id, c_ext_id))
        return True

    #TODO move this code (get exportable image) and also some code in product_image.py and sale.py in base_sale_multichannel or in a new module in order to be more generic
    def get_exportable_images(self, cr, uid, external_session, ids, context=None):
        shop = external_session.sync_from_object
        image_obj = self.pool.get('product.images')
        images_exportable_ids = image_obj.search(cr, uid, [('product_id', 'in', ids)], context=context)
        images_to_update_ids = image_obj.get_all_oeid_from_referential(cr, uid, external_session.referential_id.id, context=None)
        images_to_create = [x for x in images_exportable_ids if not x in images_to_update_ids]
        if shop.last_images_export_date:
            images_to_update_ids = image_obj.search(cr, uid, [('id', 'in', images_to_update_ids), '|', ('create_date', '>', shop.last_images_export_date), ('write_date', '>', shop.last_images_export_date)], context=context)
        return {'to_create' : images_to_create, 'to_update' : images_to_update_ids}

    def _mag_import_product_links_type(self, cr, uid, product, link_type, external_session, context=None):
        if context is None: context = {}
        conn = external_session.connection
        product_link_obj = self.pool.get('product.link')
        selection_link_types = product_link_obj.get_link_type_selection(cr, uid, context)
        mag_product_id = self.get_extid(
            cr, uid, product.id, external_session.referential_id.id, context=context)
        # This method could be completed to import grouped products too, you know, for Magento a product link is as
        # well a cross-sell, up-sell, related than the assignment between grouped products
        if link_type in [ltype[0] for ltype in selection_link_types]:
            product_links = []
            try:
                product_links = conn.call('product_link.list', [link_type, mag_product_id])
            except Exception, e:
                self.log(cr, uid, product.id, "Error when retrieving the list of links in Magento for product with reference %s and product id %s !" % (product.default_code, product.id,))
                conn.logger.debug("Error when retrieving the list of links in Magento for product with reference %s and product id %s !" % (product.magento_sku, product.id,))

            for product_link in product_links:
                linked_product_id = self.get_or_create_oeid(
                    cr, uid,
                    external_session,
                    product_link['product_id'],
                    context=context)
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
                conn.logger.info("Successfully imported product link of type %s on product %s to product %s" %(link_type, product.id, linked_product_id))
        return True

    def mag_import_product_links_types(self, cr, uid, ids, link_types, external_session, context=None):
        if isinstance(ids, (int, long)): ids = [ids]
        for product in self.browse(cr, uid, ids, context=context):
            for link_type in link_types:
                self._mag_import_product_links_type(cr, uid, product, link_type, external_session, context=context)
        return True

    def mag_import_product_links(self, cr, uid, ids, external_session, context=None):
        link_types = self.pool.get('external.referential').get_magento_product_link_types(cr, uid, external_session.referential_id.id, external_session.connection, context=context)
        local_cr = pooler.get_db(cr.dbname).cursor()
        try:
            for product_id in ids:
                self.mag_import_product_links_types(local_cr, uid, [product_id], link_types, external_session, context=context)
                local_cr.commit()
        finally:
            local_cr.close()
        return True
