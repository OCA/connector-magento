# -*- encoding: utf-8 -*-
#################################################################################
#                                                                               #
#    magentoerpconnect_configurable_product for OpenERP                         #
#    Copyright (C) 2011 Akretion Sébastien BEAU <sebastien.beau@akretion.com>   #
#                                                                               #
#    This program is free software: you can redistribute it and/or modify       #
#    it under the terms of the GNU Affero General Public License as             #
#    published by the Free Software Foundation, either version 3 of the         #
#    License, or (at your option) any later version.                            #
#                                                                               #
#    This program is distributed in the hope that it will be useful,            #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of             #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the              #
#    GNU Affero General Public License for more details.                        #
#                                                                               #
#    You should have received a copy of the GNU Affero General Public License   #
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.      #
#                                                                               #
#################################################################################

from openerp.osv.orm import Model
from openerp.osv import fields
import netsvc

class product_variant_dimension_type(Model):
    _inherit = "product.variant.dimension.type"
    _columns = {
        'magento_attribut': fields.many2one('magerp.product_attributes', 'magento_attributs',
                                            domain="[('frontend_input', '=', 'select'), ('is_global', '=', True), ('is_configurable', '=', True)]"),
        }


class product_variant_dimension_option(Model):
    _inherit = "product.variant.dimension.option"
    _columns = {
        'magento_attribut_option': fields.many2one('magerp.product_attribute_options', 'magento_attributs_option',
                                                   domain="[('attribute_id', '=', parent.magento_attribut)]"),
        }


class product_product(Model):
    _inherit = "product.product"

    #TODO for update A configurable product have to be updated if a variant is added
    def build_product_code_and_properties(self, cr, uid, ids, context=None):
        super(product_product, self).build_product_code_and_properties(cr, uid, ids, context=context)
        magento_product_exportable_ids = []
        for product in self.browse(cr, uid, ids, context=context):
            if product.product_tmpl_id.magento_exportable:
                magento_product_exportable_ids += [product.id]
        vals = {'magento_exportable':True}
#        visibility_attribut_id = self.pool.get('magerp.product_attributes').search(cr, uid, [('field_name', '=', 'x_magerp_visibility')], context=context)
#        if visibility_attribut_id:
#            option_id = self.pool.get('magerp.product_attribute_options').search(cr, uid, [('attribute_id', '=', visibility_attribut_id[0]), ('label', '=', 'Not Visible Individually')], context=context)[0]
#            vals['x_magerp_visibility'] = option_id
        self.write(cr, uid, magento_product_exportable_ids, vals, context=context)
        return True

    def generate_variant_name(self, cr, uid, product_id, context=None):
        res = super(product_product, self).generate_variant_name(cr, uid, product_id, context)
        if res == '':
            return 'Magento Configurable Product'
        return res

    def generate_product_code(self, cr, uid, product_obj, code_generator, context=None):
        res = super(product_product, self).generate_product_code(cr, uid, product_obj, code_generator, context)
        return res

    def create(self, cr, uid, vals, context):
        if context.get('generate_from_template', False):
            if vals['dimension_value_ids'] == [(6,0,[])]:
                vals['product_type'] = 'configurable'
            else:
                vals['product_type'] = 'simple'
        return super(product_product, self).create(cr, uid, vals, context)

    def _filter_fields_to_return(self, cr, uid, field_names, context):
        #In the cas that the magento view is open from the button 'open magento fields', we can give a very customize view because only on for one product
        field_names = super(product_product, self)._filter_fields_to_return(cr, uid, field_names, context)
        if context.get('open_from_button_object_id', False):
            product = self.read(cr, uid, context['open_from_button_object_id'], ['is_multi_variants', 'dimension_type_ids'], context=context)[0]
            if product['is_multi_variants'] and product['dimension_type_ids']:
                for dimension in self.pool.get('product.variant.dimension.type').browse(cr, uid, product['dimension_type_ids'], context=context):
                    field_names.remove(dimension.magento_attribut.field_name)
        return field_names


    def ext_create(self, cr, uid, external_session, resources, mapping=None, mapping_id=None, context=None):
        conn = external_session.connection
        ext_create_ids = {}
        for resource_id in resources:
            resource = resources[resource_id][context['main_lang']]
            if resource['type_id'] == 'configurable':
                is_configurable = True
                conf_attr_ids = resource.get('conf_attr_ids')
                conf_variant_ids = resource.get('conf_variant_ids')
            else:
                is_configurable = False
            ext_create_ids[resource_id] = super(product_product, self).ext_create(cr, uid, external_session, {resource_id: resources[resource_id]}, context=context)[resource_id]

            if is_configurable:
                if conf_attr_ids:
                    product_ext_id = ext_create_ids[resource_id]
                    for conf_attr_id in conf_attr_ids:
                        conn.call('ol_catalog_product_link.setSuperAttributeValues',[product_ext_id, conf_attr_id])
                    conn.call('ol_catalog_product_link.assign', [product_ext_id, conf_variant_ids])

        return ext_create_ids


    def ext_update(self, cr, uid, external_session, resources, mapping=None, mapping_id=None, context=None):
        conn = external_session.connection
        ext_update_ids = {}
        for resource_id in resources:
            resource = resources[resource_id][context['main_lang']]
            if resource['type_id'] == 'configurable':
                is_configurable = True
                product_ext_id = resource['ext_id']
                conf_attr_ids = resource.get('conf_attr_ids')
                conf_variant_ids = resource.get('conf_variant_ids')
            else:
                is_configurable = False

            ext_update_ids = super(product_product, self).ext_update(cr, uid, external_session, resources, context=context)

            if is_configurable:
                if conf_attr_ids:
                    for conf_attr_id in conf_attr_ids:
                        conn.call('ol_catalog_product_link.setSuperAttributeValues',[product_ext_id, conf_attr_id])
                    conn.call('ol_catalog_product_link.assign', [product_ext_id, conf_variant_ids])

        return ext_update_ids


class product_template(Model):
    _inherit = "product.template"
    _columns = {
        'magento_exportable':fields.boolean('Exported all variant to Magento?'),
        }


    #TODO improve me, it will be great to have the posibility to create various configurable per template
    def _create_variant_list(self, cr, ids, uid, vals, context=None):
        res = super(product_template, self)._create_variant_list(cr, ids, uid, vals, context)
        res = res + [[]]
        return res



