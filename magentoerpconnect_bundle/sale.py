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


class sale_order(Model):
    _inherit = "sale.order"

    def _merge_sub_items(self, cr, uid, product_type, top_item, child_items, context=None):
        if product_type == 'bundle':
            item = top_item.copy()
            item['bundle_configuration'] = []
            for child in child_items:
                item['bundle_configuration'].append(
                        {'product_id': int(child['product_id']),
                         'qty_ordered': float(child['qty_ordered'])})
            return item
        else:
            return super(sale_order, self)._merge_sub_items(cr, uid, product_type,
                                            top_item, child_items, context=context)
