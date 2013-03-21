# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Joël Grand-Guillaume
#    Copyright 2013 Camptocamp SA
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

from openerp.osv import fields, orm


class magento_account_invoice(orm.Model):
    _name = 'magento.account.invoice'
    _inherit = 'magento.binding'
    _inherits = {'account.invoice': 'openerp_id'}

    _columns = {
        'openerp_id': fields.many2one('account.invoice',
                                      string='Invoice',
                                      required=True,
                                      ondelete='cascade'),
        'magento_order_id': fields.many2one('magento.sale.order',
                                            string='Magento Sale Order',
                                            ondelete='set null'),
    }

    _sql_constraints = [
        ('magento_uniq', 'unique(backend_id, magento_id)',
         'An invoice with the same ID on Magento already exists.'),
    ]


class account_invoice(orm.Model):
    _inherit = 'account.invoice'

    _columns = {
        'magento_bind_ids': fields.one2many(
            'magento.account.invoice', 'openerp_id',
            string="Magento Bindings"),
    }
