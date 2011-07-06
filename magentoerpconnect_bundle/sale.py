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


class sale_order(osv.osv):
    _inherit = "sale.order"

    def get_order_lines(self, cr, uid, res, external_referential_id, data_record, key_field, mapping_lines, defaults, context):
        bundle_configuration = {}
        item_filtred=[]
        #First all bundle child are remove for the order line
        for item in data_record['items']:
            if item['parent_item_id'] and 'bundle_selection_attributes'in item['product_options']:
                if bundle_configuration.get(item['parent_item_id'], False):
                    bundle_configuration[item['parent_item_id']].append({'product_id' : int(item['product_id']) , 'qty_ordered' : float(item['qty_ordered'])})
                else:
                    bundle_configuration[item['parent_item_id']] = [{'product_id' : int(item['product_id']) , 'qty_ordered' : float(item['qty_ordered'])}]
            else:
                item_filtred.append(item)
                
        #now add the bundle configuration to bundle product
        for item in item_filtred:
            if bundle_configuration.get(item['item_id'], False):
                item['bundle_configuration'] = bundle_configuration[item['item_id']]

        data_record['items'] = item_filtred
        return super(sale_order, self).get_order_lines(cr, uid, res, external_referential_id, data_record, key_field, mapping_lines, defaults, context=context)
    
sale_order()
