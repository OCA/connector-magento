# -*- coding: utf-8 -*-
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

from openerp.osv import fields, orm
from .magerp_osv import MagerpModel
from openerp.addons.connector.decorator import only_for_referential



# TODO common AbstractModel for the 'bind' models
# TODO migrate from res.partner

class res_partner(orm.Model):
    _inherit = 'res.partner'

    _columns = {
        'magento_bind_ids': fields.one2many(
            'magento.res.partner', 'openerp_id',
            string="Magento Bindings"),
        'birthday': fields.date('Birthday'),
        'magento_address_bind_ids': fields.one2many(
            'magento.address', 'openerp_id',
            string="Magento Address Bindings"),
        'company': fields.char('Company', size=64),
    }


class magento_res_partner(orm.Model):
    _name = 'magento.res.partner'
    _inherit = 'magento.binding'
    _inherits = {'res.partner': 'openerp_id'}

    _rec_name = 'website_id'

    def _get_mag_partner_from_website(self, cr, uid, ids, context=None):
        mag_partner_obj = self.pool['magento.res.partner']
        return mag_partner_obj.search(cr, uid,
                                [('website_id', 'in', ids)],
                                context=context)

    _columns = {
        'openerp_id': fields.many2one('res.partner',
                                      string='Partner',
                                      required=True,
                                      ondelete='cascade'),
        'backend_id': fields.related('website_id', 'backend_id',
                                     type='many2one',
                                     relation='magento.backend',
                                     string='Magento Backend',
                                     store={
                                        'magento.res.partner':
                                        (lambda self, cr, uid, ids, c=None: ids, 
                                         ['website_id'], 
                                         10),
                                        'magento.website':
                                        (_get_mag_partner_from_website,
                                         ['backend_id'], 
                                         20),
                                        },
                                     readonly=True),
        'website_id': fields.many2one('magento.website',
                                      string='Magento Website',
                                      required=True,
                                      ondelete='restrict'),
        'group_id': fields.many2one('magento.res.partner.category',
                                    string='Magento Group (Category)'),
        'created_at': fields.datetime('Created At (on Magento)',
                                      readonly=True),
        'updated_at': fields.datetime('Updated At (on Magento)',
                                      readonly=True),
        'emailid': fields.char('E-mail address'),
        'taxvat': fields.char('Magento VAT'),
        'newsletter': fields.boolean('Newsletter'),
    }

    _sql_constraints = [
        ('magento_uniq', 'unique(website_id, magento_id)',
         'A partner with same ID on Magento already exists for this website.'),
    ]


class magento_address(orm.Model):
    _name = 'magento.address'
    _inherit = 'magento.binding'
    _inherits = {'res.partner': 'openerp_id'}

    _rec_name = 'backend_id'

    def _get_mag_address_from_partner(self, cr, uid, ids, context=None):
        mag_address_obj = self.pool['magento.address']
        return mag_address_obj.search(cr, uid,
                                [('magento_partner_id', 'in', ids)],
                                context=context)

    _columns = {
        'openerp_id': fields.many2one('res.partner',
                                      string='Partner',
                                      required=True,
                                      ondelete='cascade'),
        'created_at': fields.datetime('Created At (on Magento)',
                                      readonly=True),
        'updated_at': fields.datetime('Updated At (on Magento)',
                                      readonly=True),
        'is_default_billing': fields.boolean('Default Invoice'),
        'is_default_shipping': fields.boolean('Default Shipping'),
        'magento_partner_id': fields.many2one('magento.res.partner',
                                              string='Magento Partner',
                                              required=True,
                                              ondelete='cascade'),
        'backend_id': fields.related('magento_partner_id', 'backend_id',
                                     type='many2one',
                                     relation='magento.backend',
                                     string='Magento Backend',
                                     store={
                                        'magento.address':
                                        (lambda self, cr, uid, ids, c=None: ids, 
                                         ['magento_partner_id'], 
                                         10),
                                        'magento.res.partner':
                                        (_get_mag_address_from_partner,
                                         ['backend_id', 'website_id'], 
                                         20),
                                        },
                                     readonly=True),
        'website_id': fields.related('magento_partner_id', 'website_id',
                                     type='many2one',
                                     relation='magento.website',
                                     string='Magento Website',
                                     store={
                                        'magento.address':
                                        (lambda self, cr, uid, ids, c=None: ids, 
                                         ['magento_partner_id'], 
                                         10),
                                        'magento.res.partner':
                                        (_get_mag_address_from_partner,
                                         ['website_id'], 
                                         20),
                                        },
                                     readonly=True),
    }

    _sql_constraints = [
        ('magento_uniq', 'unique(backend_id, magento_id)',
         'A partner address with same ID on Magento already exists.'),
    ]


class res_partner_category(orm.Model):
    _inherit = 'res.partner.category'

    _columns = {
        'magento_bind_ids': fields.one2many(
            'magento.res.partner.category',
            'openerp_id',
            string='Magento Bindings',
            readonly=True),
    }


class magento_res_partner_category(orm.Model):
    _name = 'magento.res.partner.category'
    _inherit = 'magento.binding'
    _inherits = {'res.partner.category': 'openerp_id'}

    _columns = {
        'openerp_id': fields.many2one('res.partner.category',
                                       string='Partner Category',
                                       required=True,
                                       ondelete='cascade'),
        #TODO : replace by a m2o when tax class will be implemented
        'tax_class_id': fields.integer('Tax Class ID'),
    }

    _sql_constraints = [
        ('magento_uniq', 'unique(backend_id, magento_id)',
         'A partner tag with same ID on Magento already exists.'),
    ]



# TODO: migrate the models below:
# class res_partner(MagerpModel):
#     _inherit = "res.partner"

#     _columns = {
#         'group_id':fields.many2one('res.partner.category', 'Magento Group(Category)'),
#         'store_id':fields.many2one('magerp.storeviews', 'Last Store View', help="Last store view where the customer has bought."),
#         'store_ids':fields.many2many('magerp.storeviews', 'magerp_storeid_rel', 'partner_id', 'store_id', 'Store Views'),
#         'website_id':fields.many2one('external.shop.group', 'Magento Website', help='Select a website for which the Magento customer will be bound.'),
#         'created_in':fields.char('Created in', size=100),
#         'created_at':fields.datetime('Created Date'),
#         'updated_at':fields.datetime('Updated At'),
#         'emailid':fields.char('Email Address', size=100, help="Magento uses this email ID to match the customer. If filled, if a Magento customer is imported from the selected website with the exact same email, he will be bound with this partner and this latter will be updated with Magento's values."),
#         'mag_vat':fields.char('Magento VAT', size=50, help="To be able to receive customer VAT number you must set it in Magento Admin Panel, menu System / Configuration / Client Configuration / Name and Address Options."),
#         'mag_birthday':fields.date('Birthday', help="To be able to receive customer birthday you must set it in Magento Admin Panel, menu System / Configuration / Client Configuration / Name and Address Options."),
#         'mag_newsletter':fields.boolean('Newsletter'),
#         'magento_pwd': fields.char('Magento Password', size=256),
#         }


# class res_partner_category(MagerpModel):
#     _inherit = "res.partner.category"
#     _columns = {'tax_class_id':fields.integer('Tax Class ID'),
#                 }
