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

from osv import osv, fields
import netsvc

class product_variant_dimension_type(osv.osv):
    
    _inherit = "product.variant.dimension.type"
    

    _columns = {
        'magento_attribut': fields.many2one('magerp.product_attributes', 'magento_attributs', domain = "[('frontend_input', '=', 'select'), ('is_global', '=', True), ('is_configurable', '=', True)]"),
    }

product_variant_dimension_type()


class product_variant_dimension_option(osv.osv):
    
    _inherit = "product.variant.dimension.option"
    

    _columns = {
        #'magento_attribut': fields.related('dimension_id', 'magento_attribut', type="many2one", relation="magerp.product_attributes", string="Magento attributs", readonly=True),
        'magento_attribut_option': fields.many2one('magerp.product_attribute_options', 'magento_attributs_option', domain = "[('attribute_id', '=', parent.magento_attribut)]"),

    }


product_variant_dimension_option()

class product_product(osv.osv):
    
    _inherit = "product.product"

    def build_product_code_and_properties(self, cr, uid, ids, context=None):
        super(product_product, self).build_product_code_and_properties(cr, uid, ids, context=context)
        magento_product_exportable_ids = []
        for product in self.browse(cr, uid, ids, context=context):
            if product.product_tmpl_id.magento_exportable:
                magento_product_exportable_ids += [product.id]
        self.write(cr, uid, magento_product_exportable_ids, {'magento_exportable':True}, context=context)
        return True

    def configurable_product_are_supported(self):
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
        super(product_product, self).create(cr, uid, vals, context)

    def ext_export_configurable(self, cr, uid, id, external_referential_ids, defaults, context):
        '''check if all simple product are already exported if not it export the unexported product'''
        shop = self.pool.get('sale.shop').browse(cr, uid, context['shop_id'])
        variant_ids = self.read(cr, uid, id, ['variant_ids'], context)['variant_ids']
        variant_ids.remove(id)
        for id in variant_ids:
            if not self.oeid_to_extid(cr, uid, id, shop.referential_id.id):
                context['do_not_update_date'] = True 
                self.ext_export(cr, uid, [id], external_referential_ids, defaults, context)
        return True

    def add_data_to_create_configurable_product(self, cr, uid, oe_id, data, context=None):
        shop = self.pool.get('sale.shop').browse(cr, uid, context['shop_id'])
        # check if not already created
        products_data = {} # values of the attributes used on the element products
        attributes_data = {} # params of the attributes to use on the configurable product

        variant_ids = self.read(cr, uid, oe_id, ['variant_ids'], context=context)['variant_ids']
        variant_ids.remove(oe_id)
        if variant_ids:
            associated_skus = []
            # create a dict with all values used on the configurable products
            for product in self.browse(cr, uid, variant_ids):
                associated_skus += [product.magento_sku]
                attr_list = set()
                # get values for each attribute of the product
                mag_prod_id = str(self.oeid_to_extid(cr, uid, product.id, shop.referential_id.id))
                products_data[mag_prod_id] = {}
                index=0
                for value in product.dimension_value_ids:
                    # get the option selected on the product
                    option = value.option_id.magento_attribut_option
                    attr = option.attribute_id
                    attr_list = attr_list.union(set([attr]))
                    prod_data = {
                        'attribute_id': attr.magento_id, # id of the attribute
                        'label': option.label, # label of the option
                        'value_index': int(option.value), # id of the option
                        'is_percent': 0, # modification of the price
                        'pricing_value': '', # modification of the price
                    }
                    #products_data[mag_prod_id][str(attribute_set.configurable_attributes.index(attr))] = prod_data
                    products_data[mag_prod_id][str(index)] = prod_data
                    index += 1

            # create a dict with attributes used on the configurable product
            index=-1
            for attr in attr_list:
                index += 1
                attr_data = {
                             #'id': False,
                             'label': '',
                             #'position': False,
                             'values': [],
                             'attribute_id': attr.magento_id, # id of the attribute on magento
                             'attribute_code': attr.attribute_code, # code of the attribute on magento
                             'frontend_label': attr.frontend_label, # label of the attribute on magento
                             'html_id': "config_super_product__attribute_%s" % index, # must be config_super_product__attribute_ with an increment
                }
                attr_values = []
                for prod_id in products_data:
                    [attr_values.append(products_data[prod_id][key]) for key in products_data[prod_id] if products_data[prod_id][key]['attribute_id'] == attr.magento_id]
                attr_data.update({'values': attr_values})
                attributes_data.update({str(index): attr_data})
        data.update({'configurable_products_data': products_data, 'configurable_attributes_data': attributes_data, 'associated_skus':associated_skus})
        return data


    def ext_create(self, cr, uid, data, conn, method, oe_id, context):
        if data.get('type_id', False) == 'configurable':
            data = self.add_data_to_create_configurable_product(cr, uid, oe_id, data, context)
        return super(product_product, self).ext_create(cr, uid, data, conn, method, oe_id, context)

    def extdata_from_oevals(self, cr, uid, external_referential_id, data_record, mapping_lines, defaults, context=None):
        #TODO maybe this mapping can be in the mapping template but the problem is that this mapping have to be apply at the end
        #because they will overwrite other mapping result. Maybe adding a sequence on the mapping will be the solution
        res = super(product_product, self).extdata_from_oevals(cr, uid, external_referential_id, data_record, mapping_lines, defaults, context)
        if data_record.get('is_multi_variants', False):
            for dim_value in self.pool.get('product.variant.dimension.value').browse(cr, uid, data_record['dimension_value_ids'], context=context):
                res[dim_value.dimension_id.magento_attribut.attribute_code] = dim_value.option_id.magento_attribut_option.value
        return res
    
    def _filter_fields_to_return(self, cr, uid, field_names, context):
        #In the cas that the magento view is open from the button 'open magento fields', we can give a very customize view because only on for one product
        field_names = super(product_product, self)._filter_fields_to_return(cr, uid, field_names, context)
        if context.get('open_from_button_object_id', False):
            product = self.read(cr, uid, context['open_from_button_object_id'], ['is_multi_variants', 'dimension_type_ids'], context=context)[0]
            if product['is_multi_variants'] and product['dimension_type_ids']:
                for dimension in self.pool.get('product.variant.dimension.type').browse(cr, uid, product['dimension_type_ids'], context=context):
                    field_names.remove(dimension.magento_attribut.field_name)
        return field_names


product_product()

class product_template(osv.osv):

    _inherit = "product.template"

    _columns = {
        'magento_exportable':fields.boolean('Exported all variant to Magento?'),
    }

    def _create_variant_list(self, cr, ids, uid, vals, context=None):
        res = super(product_template, self)._create_variant_list(cr, ids, uid, vals, context)
        res = res + [[]]
        return res

product_template()



