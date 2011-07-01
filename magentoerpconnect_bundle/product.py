# -*- encoding: utf-8 -*-
#################################################################################
#                                                                               #
#    magentoerpconnect_bundle for OpenERP                                       #
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


class product_product(osv.osv):
    _inherit = "product.product"
    
    def get_depends(self, cr, uid, id, product_type, context=None):
        product_depends, child_to_parent_product_depends = super(product_product, self).get_depends(cr, uid, id, product_type, context=None)       
        if product_type == 'configurable':
            component_ids = []
            product = self.browse(cr, uid, id, context=context)
            for product_item_set in product.item_set_ids:
                for product_item_set_line in product_item_set.item_set_line_ids:
                    component_ids += product_item_set_line.product.id
            
            component_ids_to_export = list(set(component_ids) & set(ids))
            if component_ids_to_export:
                product_depends[id] = component_ids_to_export
                for component_id in component_ids_to_export:
                    child_to_parent_product_depends[component_id] = id
                return product_depends, child_to_parent_product_depends, True
        return product_depends, child_to_parent_product_depends, False
                    
                    
    def bundle_product_are_supported(self):
        return True
    
    def get_bundle_component(cr, uid, ids, context):
        res = {}
        for product in self.browse(cr, uid, product_read[0], context=context)
            res[product.id] = []
            for product_item_set in product.item_set_ids:
                for product_item_set_line in product_item_set.item_set_line_ids:
                    res[product.id] += product_item_set_line.product.id
        return res
    
    def action_before_exporting(self, cr, uid, id, product_type, external_referential_ids, defaults, context=None):
        if product_type == 'bundle':
            # Check if all simple product are already exported if not it export the unexported product
            shop = self.pool.get('sale.shop').browse(cr, uid, context['shop_id'])
            component_ids = self.get_bundle_component(cr, uid, [id], context)[id]
            for id in component_ids:
                if not self.oeid_to_extid(cr, uid, id, shop.referential_id.id):
                    context['do_not_update_date'] = True 
                    self.ext_export(cr, uid, [id], external_referential_ids, defaults, context)
        return super(self, product_product).action_before_exporting(cr, uid, id, product_type, external_referential_ids, defaults, context=context)
    

    def add_data_to_create_bundle_product(self, cr, uid, oe_id, data, context=None):
        shop = self.pool.get('sale.shop').browse(cr, uid, context['shop_id'])
        # check if not already created


        #TODO add the data
        
        data.update({'configurable_products_data': products_data, 'configurable_attributes_data': attributes_data, 'associated_skus':associated_skus})
        return data

    
    def ext_create(self, cr, uid, data, conn, method, oe_id, context):
        if data.get('type_id', False) == 'bundle':
            data = self.add_data_to_create_bundle_product(cr, uid, oe_id, data, context)
        return super(product_product, self).ext_create(cr, uid, data, conn, method, oe_id, context)
    

product_product()

