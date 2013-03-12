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

from openerp.osv.orm import Model

import logging
_logger = logging.getLogger(__name__)


class magento_stock_picking(orm.Model):
    _name = 'magento.stock.picking'
    _inherit = 'magento.binding'
    _inherits = {'stock.picking': 'openerp_id'}

    _columns = {
        'openerp_id': fields.many2one('stock.picking',
                                      string='Stock Picking',
                                      required=True,
                                      ondelete='cascade'),
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



# TO REVIEW 
class stock_picking(Model):

    _inherit = "stock.picking"

    def add_ext_tracking_reference(self, cr, uid, id, carrier_id, ext_shipping_id, context=None):
        if context is None: context = {}
        conn = context.get('conn_obj', False)
        carrier = self.pool.get('delivery.carrier').read(cr, uid, carrier_id, ['magento_carrier_code', 'magento_tracking_title'], context)

        if self.pool.get('ir.model.fields').search(cr, uid, [('name', '=', 'carrier_tracking_ref'), ('model', '=', 'stock.picking')]): #OpenERP v6 have the field carrier_tracking_ref on the stock_picking but v5 doesn't have it
            carrier_tracking_ref = self.read(cr, uid, id, ['carrier_tracking_ref'], context)['carrier_tracking_ref']
        else:
            carrier_tracking_ref = ''

        res = conn.call('sales_order_shipment.addTrack', [ext_shipping_id, carrier['magento_carrier_code'], carrier['magento_tracking_title'] or '', carrier_tracking_ref or ''])
        if res:
            _logger.info("Successfully adding a tracking reference to the shipping with OpenERP id %s and ext id %s in external sale system", id, ext_shipping_id)
        return True
