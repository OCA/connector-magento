# -*- encoding: utf-8 -*-
#########################################################################
#This module intergrates Open ERP with the magento core                 #
#Core settings are stored here                                          #
#########################################################################
#                                                                       #
# Copyright (C) 2009  Sharoon Thomas, Raphaël Valyi                     #
# Copyright (C) 2011 Akretion Sébastien BEAU sebastien.beau@akretion.com#
# Copyright (C) 2011 Camptocamp Guewen Baconnier                        # 
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
from tools.translate import _
import magerp_osv

class res_partner_category(magerp_osv.magerp_osv):
    _inherit = "res.partner.category"
    
    _columns = {
                    'tax_class_id':fields.integer('Tax Class ID'),
                }
res_partner_category()

class res_partner_address(magerp_osv.magerp_osv):
    _inherit = "res.partner.address"
    
    _columns = {
                    'firstname':fields.char('First Name', size=100),
                    'lastname':fields.char('Last Name', size=100),
                    'is_magento_order_address':fields.boolean('Magento Order Address?'), #TODO still needed?
                }
    _defaults = {
                    'is_magento_order_address': lambda * a:False,
                 }    
res_partner_address()

class res_partner(magerp_osv.magerp_osv):
    _inherit = "res.partner"

    def _is_magento_exported(self, cr, uid, ids, field_name, arg, context=None):
        """Return True if the partner is already exported to at least one magento shop
        """
        res = {}
        # get all magento external_referentials
        referentials = self.pool.get('external.referential').search(cr, uid, [('magento_referential', '=', True)])
        for partner in self.browse(cr, uid, ids, context):
            for referential in referentials:
                res[partner.id] = False
                if self.oeid_to_extid(cr, uid, partner.id, referential, context):
                    res[partner.id] = True
                    break
        return res

    _columns = {
                    'group_id':fields.many2one('res.partner.category', 'Magento Group(Category)'),
                    'store_id':fields.many2one('magerp.storeviews', 'Last Store View', readonly=True, help="Last store view where the customer has bought."),
                    'store_ids':fields.many2many('magerp.storeviews', 'magerp_storeid_rel', 'partner_id', 'store_id', 'Store Views', readonly=True),
                    'website_id':fields.many2one('external.shop.group', 'Magento Website', help='Select a website for which the Magento customer will be bound.'),
                    'created_in':fields.char('Created in', size=100),
                    'created_at':fields.datetime('Created Date'),
                    'updated_at':fields.datetime('Updated At'),
                    'emailid':fields.char('Email Address', size=100, help="Magento uses this email ID to match the customer. If filled, if a Magento customer is imported from the selected website with the exact same email, he will be bound with this partner and this latter will be updated with Magento's values."),
                    'mag_vat':fields.char('Magento VAT', size=50, help="To be able to receive customer VAT number you must set it in Magento Admin Panel, menu System / Configuration / Client Configuration / Name and Address Options."),
                    'mag_birthday':fields.date('Birthday', help="To be able to receive customer birthday you must set it in Magento Admin Panel, menu System / Configuration / Client Configuration / Name and Address Options."),
                    'mag_newsletter':fields.boolean('Newsletter'),
                    'magento_exported': fields.function(_is_magento_exported, type="boolean", method=True, string="Exists on Magento"),
                }

    _sql_constraints = [('emailid_uniq', 'unique(emailid, website_id)', 'A partner already exists with this email address on the selected website.')]

res_partner()
