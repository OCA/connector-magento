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

from openerp.osv.orm import Model

class product_product(Model):
    _inherit = "product.product"

    def get_bundle_component(self, cr, uid, ids, context):
        res = {}
        for product in self.browse(cr, uid, ids, context=context):
            res[product.id] = []
            for product_item_set in product.item_set_ids:
                for product_item_set_line in product_item_set.item_set_line_ids:
                    res[product.id].append(product_item_set_line.product_id.id)
        return res

    def action_before_exporting(self, cr, uid, id, product_type, external_referential_ids, defaults, context=None):
        #When the export of a bundle product is forced we should check if all variant are already exported
        if context.get('force_export', False) and product_type == 'bundle':
            shop = self.pool.get('sale.shop').browse(cr, uid, context['shop_id'])
            component_ids = self.get_bundle_component(cr, uid, [id], context)[id]
            for id in component_ids:
                if not self.oeid_to_extid(cr, uid, id, shop.referential_id.id):
                    self.ext_export(cr, uid, [id], external_referential_ids, defaults, context)
        return super(product_product, self).action_before_exporting(cr, uid, id, product_type, external_referential_ids, defaults, context=context)


    def add_data_to_create_bundle_product(self, cr, uid, oe_id, data, context=None):
        shop = self.pool.get('sale.shop').browse(cr, uid, context['shop_id'])
        # check if not already created
        #TODO add the data
        data.update({'configurable_products_data': products_data,
                     'configurable_attributes_data': attributes_data,
                     'associated_skus':associated_skus})
        return data

    def ext_create(self, cr, uid, data, conn, method, oe_id, context):
        if data.get('type_id', False) == 'bundle':
            data = self.add_data_to_create_bundle_product(cr, uid, oe_id, data, context)
        return super(product_product, self).ext_create(cr, uid, data, conn, method, oe_id, context)

