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
    
    def merge_parent_item_line_with_child(self, cr, uid, item, items_child, context=None):
        if item['product_type'] == 'bundle':
            item['bundle_configuration'] = []
            for child in items_child[item['item_id']]:
                item['bundle_configuration'].append({'product_id' : int(child['product_id']) , 'qty_ordered' : float(child['qty_ordered'])})
        return super(sale_order, self).merge_parent_item_line_with_child(cr, uid, item, items_child, context=context)
    
sale_order()
