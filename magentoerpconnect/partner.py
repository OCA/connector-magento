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
class magento_res_partner(orm.Model):
    _name = 'magento.res.partner'

    _rec_name = 'website_id'

    _columns = {
        'partner_id': fields.many2one('res.partner', string='Partner'),
        'magento_id': fields.integer('ID on Magento'),
        'backend_id': fields.related('website_id', 'backend_id',
                                     type='many2one',
                                     relation='magento.backend',
                                     string='Magento Backend'),
        'website_id': fields.many2one('magento.website',
                                      string='Magento Website',
                                      required=True),
        'group_id': fields.many2one('magento.res.partner.category',
                                    string='Magento Group (Category)'),
        'created_at': fields.datetime('Created At'),
        'updated_at': fields.datetime('Updated At'),
        'email': fields.char('E-mail address'),
        'taxvat': fields.char('Magento VAT'),
        'newsletter': fields.boolean('Newsletter'),
    }

    _sql_constraints = [
        ('partner_uniq', 'unique(partner_id, website_id)',
         'Partner with same ID on Magento already exists.'),
    ]


class res_partner(orm.Model):
    _inherit = 'res.partner'

    _columns = {
        'magento_bind_ids': fields.one2many(
            'magento.res.partner', 'partner_id',
            string="Magento Bindings"),
        'birthday': fields.date('Birthday'),
    }


class res_partner_category(orm.Model):
    _inherit = 'res.partner.category'

    _columns = {
        'magento_bind_ids': fields.one2many(
            'magento.res.partner.category',
            'category_id',
            string='Magento Bindings',
            readonly=True),
    }


class magento_res_partner_category(orm.Model):
    _name = 'magento.res.partner.category'

    _inherits = {'res.partner.category': 'category_id'}

    _columns = {
        'category_id': fields.many2one('res.partner.category',
                                       string='Partner Category',
                                       required=True,
                                       ondelete='cascade'),
        'magento_id': fields.integer('ID on Magento'),
        'backend_id': fields.many2one(
            'magento.backend',
            'Magento Backend',
            required=True),
        'tax_class_id': fields.integer('Tax Class ID'),
    }

    _sql_constraints = [
        ('magento_uniq', 'unique(backend_id, magento_id)',
         'Partner Tag with same ID on Magento already exists.'),
    ]



# TODO: migrate the models below:
# fields are left for data migration
class res_partner(MagerpModel):
    _inherit = "res.partner"

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
        'magento_pwd': fields.char('Magento Password', size=256),
        }


class res_partner_category(MagerpModel):
    _inherit = "res.partner.category"
    _columns = {'tax_class_id':fields.integer('Tax Class ID'),
                }
