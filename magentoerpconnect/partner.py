# -*- encoding: utf-8 -*-
#########################################################################
#This module intergrates Open ERP with the magento core                 #
#Core settings are stored here                                          #
#########################################################################
#                                                                       #
# Copyright (C) 2009  Sharoon Thomas, Raphaël Valyi                     #
# Copyright (C) 2011 Akretion Sébastien BEAU sebastien.beau@akretion.com#
# Copyright (C) 2011-2012 Camptocamp Guewen Baconnier                   #
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
from base_external_referentials.decorator import only_for_referential
import hashlib

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

    @only_for_referential('magento')
    def ext_create(self, cr, uid, external_session, resources, mapping, mapping_id, context=None):
        ext_create_ids = {}
        main_lang = context['main_lang']
        for resource_id, resource in resources.items():
            ext_id = external_session.connection.call(mapping[mapping_id]['external_create_method'],
                                         [resource[main_lang]['customer_id'], resource[main_lang]])
            ext_create_ids[resource_id] = ext_id
        return ext_create_ids

res_partner_address()

class res_partner(magerp_osv.magerp_osv):
    _inherit = "res.partner"

    def _is_magento_exported(self, cr, uid, ids, field_name, arg, context=None):
        """Return True if the partner is already exported to at least one magento shop
        """
        res = {}
        # get all magento external_referentials
        referential_ids = self.pool.get('external.referential').search(cr, uid, [('magento_referential', '=', True)])
        for partner in self.browse(cr, uid, ids, context):
            for referential_id in referential_ids:
                res[partner.id] = False
                if partner.get_extid(referential_id, context=context):
                    res[partner.id] = True
                    break
        return res

    _columns = {
                    'group_id':fields.many2one('res.partner.category', 'Magento Group(Category)'),
                    'store_id':fields.many2one('magerp.storeviews', 'Last Store View', help="Last store view where the customer has bought."),
                    'store_ids':fields.many2many('magerp.storeviews', 'magerp_storeid_rel', 'partner_id', 'store_id', 'Store Views'),
                    'website_id':fields.many2one('external.shop.group', 'Magento Website', help='Select a website for which the Magento customer will be bound.'),
                    'created_in':fields.char('Created in', size=100),
                    'created_at':fields.datetime('Created Date'),
                    'updated_at':fields.datetime('Updated At'),
                    'emailid':fields.char('Email Address', size=100, help="Magento uses this email ID to match the customer. If filled, if a Magento customer is imported from the selected website with the exact same email, he will be bound with this partner and this latter will be updated with Magento's values."),
                    'mag_vat':fields.char('Magento VAT', size=50, help="To be able to receive customer VAT number you must set it in Magento Admin Panel, menu System / Configuration / Client Configuration / Name and Address Options."),
                    'mag_birthday':fields.date('Birthday', help="To be able to receive customer birthday you must set it in Magento Admin Panel, menu System / Configuration / Client Configuration / Name and Address Options."),
                    'mag_newsletter':fields.boolean('Newsletter'),
                    'magento_exported': fields.function(_is_magento_exported, type="boolean", method=True, string="Exists on Magento"),
                    'magento_pwd': fields.char('Magento Password', size=256),
                }

    _sql_constraints = [('emailid_uniq', 'unique(emailid, website_id)', 'A partner already exists with this email address on the selected website.')]

    @only_for_referential('magento')
    def get_ids_and_update_date(self, cr, uid, external_session, ids=None, last_exported_date=None, context=None):
        store_ids = [store.id for store in external_session.sync_from_object.storeview_ids]
        query = """
        SELECT DISTINCT partner_id
        FROM magerp_storeid_rel
        LEFT JOIN res_partner
            ON magerp_storeid_rel.partner_id = res_partner.id
        LEFT JOIN ir_model_data
            ON res_partner.id = ir_model_data.res_id
            AND ir_model_data.model = 'res.partner'
            AND ir_model_data.referential_id = %(ref_id)s
        WHERE ir_model_data.res_id IS NULL AND magerp_storeid_rel.store_id IN %(store_ids)s"""
        params = {'ref_id': external_session.referential_id.id, 
                  'store_ids': tuple(store_ids)}
        cr.execute(query,params)
        results = cr.dictfetchall()
        ids = [dict_id['partner_id'] for dict_id in results]
        return ids, {}

    @only_for_referential('magento')
    def _transform_and_send_one_resource(self, cr, uid, external_session, resource, resource_id,
                            update_date, mapping, mapping_id, defaults=None, context=None):
        res = super(res_partner, self)._transform_and_send_one_resource(cr, uid, external_session, 
            resource, resource_id, update_date, mapping, mapping_id, defaults=defaults, context=context)
        if res:
            address_obj = self.pool.get('res.partner.address')
            resource_ids = address_obj.search(cr, uid, [('partner_id', '=', resource_id)], context=context)
            for resource_id in resource_ids:
                result = address_obj._export_one_resource(cr, uid, external_session, resource_id, context=context)
        return res

res_partner()
