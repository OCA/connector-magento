# -*- coding: utf-8 -*-
#########################################################################
#                                                                       #
#########################################################################
#                                                                       #
# Copyright (C) 2010 BEAU Sébastien                                     #
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

from openerp.osv import orm, fields


class magento_stock_picking(orm.Model):
    _name = 'magento.stock.picking'
    _inherit = 'magento.binding'
    _inherits = {'stock.picking': 'openerp_id'}

    _columns = {
        'openerp_id': fields.many2one('stock.picking',
                                      string='Stock Picking',
                                      required=True,
                                      ondelete='cascade'),
        'magento_order_id': fields.many2one('magento.sale.order',
                                            string='Magento Sale Order',
                                            ondelete='set null'),
    }

    _sql_constraints = [
        ('magento_uniq', 'unique(backend_id, magento_id)',
         'A stock picking with same ID on Magento already exists.'),
    ]


class stock_picking(orm.Model):
    _inherit = 'stock.picking'

    _columns = {
        'magento_bind_ids': fields.one2many(
            'magento.stock.picking', 'openerp_id',
            string="Magento Bindings"),
    }

