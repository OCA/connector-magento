#########################################################################
#This module intergrates Open ERP with the magento core                 #
#Core settings are stored here                                          #
#########################################################################
#                                                                       #
# Copyright (C) 2009  Sharoon Thomas                                    #
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
import magerp_osv

class res_partner_category(magerp_osv.magerp_osv):
    _inherit = "res.partner.category"
    _LIST_METHOD = 'ol_customer_groups.list'
    _columns = {
                    'magento_id':fields.integer('Customer Group ID'),
                    'tax_class_id':fields.integer('Tax Class ID'),
                    'instance':fields.many2one('external.referential', 'Magento Instance', readonly=True, store=True),
                }
res_partner_category()

class res_partner_address(magerp_osv.magerp_osv):
    _columns = {
                    'magento_id':fields.integer('Magento ID'),
                    'lastname':fields.char('Last Name', size=100),
                    'exportable':fields.boolean('Export to magento?'),
                    'is_magento_order_address':fields.boolean('Magento Order Address?'),
                }
    _defaults = {
                    'exportable':lambda * a:True,
                    'is_magento_order_address': lambda * a:False,
                 }
res_partner_address()

class res_partner(magerp_osv.magerp_osv):
    _columns = {
                    'magento_id':fields.integer('Magento customer ID', readonly=True, store=True),
                    'group_id':fields.many2one('res.partner.category', 'Magento Group(Category)'),
                    'store_id':fields.many2one('magerp.storeviews', 'Store'),
                    'website_id':fields.many2one('external.shop.group', 'Website'),
                    'created_in':fields.char('Created in', size=100),
                    'created_at':fields.datetime('Created Date'),
                    'updated_at':fields.datetime('Updated At'),
                    'emailid':fields.char('Email ID', size=100, help="Magento uses this email ID to correspond to the customer"),
                    'instance':fields.many2one('external.referential', 'Magento Instance', readonly=True, store=True),
                }

res_partner()
