# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier, David Beal
#    Copyright 2013 Camptocamp SA
#    Copyright 2013 Akretion
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import logging

from openerp.osv import orm, fields
from openerp.osv.osv import except_osv
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)


class magento_product_category(orm.Model):
    _name = 'magento.product.category'
    _inherit = 'magento.binding'
    _inherits = {'product.category': 'openerp_id'}

    _columns = {
        'openerp_id': fields.many2one('product.category',
                                      string='Product Category',
                                      required=True,
                                      ondelete='cascade'),
        'description': fields.text('Description', translate=True),
        'magento_parent_id': fields.many2one(
            'magento.product.category',
             string='Magento Parent Category',
             ondelete='cascade'),
        'magento_child_ids': fields.one2many(
            'magento.product.category',
             'magento_parent_id',
             string='Magento Child Categories'),
    }

    _sql_constraints = [
        ('magento_uniq', 'unique(backend_id, magento_id)',
         'A product category with same ID on Magento already exists.'),
    ]


class product_category(orm.Model):
    _inherit = 'product.category'

    _columns = {
        'magento_bind_ids': fields.one2many(
            'magento.product.category', 'openerp_id',
            string="Magento Bindings"),
    }


class magento_product_product(orm.Model):
    _name = 'magento.product.product'
    _inherit = 'magento.binding'
    _inherits = {'product.product': 'openerp_id'}

    def product_type_get(self, cr, uid, context=None):
        return [
            ('simple', 'Simple Product'),
            ('grouped', 'Grouped Product'),
            ('configurable', 'Configurable Product'),
            ('virtual', 'Virtual Product'),
            ('bundle', 'Bundle Product'),
            ('downloadable', 'Downloadable Product'),
        ]

    def _product_type_get(self, cr, uid, context=None):
        return self.product_type_get(cr, uid, context=context)

    _columns = {
        'openerp_id': fields.many2one('product.product',
                                      string='Product',
                                      required=True,
                                      ondelete='cascade'),
        'website_ids': fields.many2many('external.shop.group',
            'magerp_product_shop_group_rel', 'product_id',
            'shop_group_id', 'Websites',
            help='By defaut product will be exported on every website, if you want to export it only on some website select them here'),
        'created_at':fields.date('Created At (on Magento)'),
        'updated_at':fields.date('Updated At (on Magento)'),
        'product_type': fields.selection(_product_type_get, 'Magento Product Type'),
        'manage_stock': fields.selection([
            ('use_default','Use Default Config'),
            ('no', 'Do Not Manage Stock'),
            ('yes','Manage Stock')
            ], 'Manage Stock Level'),
        'manage_stock_shortage': fields.selection([
            ('use_default','Use Default Config'),
            ('no', 'No Sell'),
            ('yes','Sell qty < 0'),
            ('yes-and-notification','Sell qty < 0 and Use Customer Notification'),
            ], 'Manage Inventory Shortage'),
        }

    _defaults = {
        'product_type': 'simple',
        'manage_stock': 'use_default',
        'manage_stock_shortage': 'use_default',
        }

    _sql_constraints = [
        ('magento_uniq', 'unique(backend_id, magento_id)',
         "A product with the same ID on Magento already exists")
    ]


class product_product(orm.Model):
    _inherit = 'product.product'

    _columns = {
        'magento_bind_ids': fields.one2many(
            'magento.product.product',
            'openerp_id',
            string='Magento Bindings',),
    }
