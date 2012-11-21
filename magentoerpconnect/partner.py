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

import hashlib

from openerp.osv import fields
from .magerp_osv import MagerpModel
from base_external_referentials.decorator import only_for_referential

class res_partner_category(MagerpModel):
    _inherit = "res.partner.category"
    _columns = {'tax_class_id':fields.integer('Tax Class ID'),
                }

class res_partner_address(MagerpModel):
    _inherit = "res.partner.address"

    #Migration script for 6.1.0 to 6.1.1
    def _auto_init(self, cr, context=None):
        # recompute the field name with firstname + lastname
        # in order to have the same data as the data of base_partner_surname
        first_install=False
        cr.execute("SELECT column_name FROM information_schema.columns "
                   "WHERE table_name = 'res_partner_address' "
                   "AND column_name = 'firstname'")
        if cr.fetchone():
            cr.execute(
                "UPDATE res_partner_address "
                "SET name = CASE "
                  "WHEN firstname IS NOT NULL AND lastname IS NOT NULL THEN (firstname || ' ' || lastname) "
                  "WHEN firstname IS NOT NULL AND lastname IS NULL THEN firstname "
                  "WHEN firstname IS NULL AND lastname IS NOT NULL THEN lastname "
                  "ELSE name "
                "END"
                  )
            cr.execute("ALTER TABLE res_partner_address "
                       "RENAME COLUMN firstname TO first_name")
            cr.execute("ALTER TABLE res_partner_address "
                       "RENAME COLUMN lastname TO last_name")
        return super(res_partner_address, self)._auto_init(cr, context=context)

    _columns = {
        'company':fields.char('Company', size=100),
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

class res_partner(MagerpModel):
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
