# -*- coding: utf-8 -*-
#########################################################################
#                                                                       #
#########################################################################
#                                                                       #
# Copyright (C) 2011  Sharoon Thomas                                    #
# Copyright (C) 2009  Raphaël Valyi                                     #
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
from openerp.osv.osv import except_osv
import netsvc
from tools.translate import _
from openerp import tools
import time
from tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.addons.connector.external_osv import ExternalSession
from openerp.addons.connector.decorator import only_for_referential, open_report

#from connector import report

import logging
_logger = logging.getLogger(__name__)

DEBUG = True
NOTRY = False

#TODO, may be move that on out CSV mapping, but not sure we can easily
#see OpenERP sale/sale.py and Magento app/code/core/Mage/Sales/Model/Order.php for details
ORDER_STATUS_MAPPING = {
    'manual': 'processing',
    'progress': 'processing',
    'shipping_except': 'complete',
    'invoice_except': 'complete',
    'done': 'complete',
    'cancel': 'canceled',
    'waiting_date': 'holded'}
SALE_ORDER_IMPORT_STEP = 200


class sale_order_line(orm.Model):
    _inherit = 'sale.order.line'
    _columns = {
            'magento_bind_ids': fields.one2many(
                'magento.sale.order.line', 'openerp_id',
                string="Magento Bindings"),
        }

    def invoice_line_create(self, cr, uid, ids, context):
        """ In order to have a one2many link between the sale order line
        and the various invoice line, we overwrite this method.  We made
        that cause there is only a many2many link between them by
        default. We were not able to retrieve the sale order line ID on
        magento side from an invoice line.

        This is mainly used in the MagentoInvoiceSynchronizer.

        """
        created_line_ids = []
        mag_inv_line_obj = self.pool.get('magento.account.invoice.line')
        for line in self.browse(cr, uid, ids, context=context):
            created_line_id = super(sale_order_line, self).invoice_line_create(
                    cr, uid, [line.id], context)
            # Test if magento_sale_order_line exists, if yes create a
            # magento_invoice_line
            if line.magento_bind_ids:
                vals = {
                    'openerp_id': created_line_id[0],
                    'magento_order_line_id': line.id
                }
                mag_inv_line_obj.create(cr, uid, ids, vals, context)
            created_line_ids.append(created_line_id[0])
        return created_line_ids


class magento_sale_order_line(orm.Model):
    _name = 'magento.sale.order.line'
    _inherit = 'magento.binding'
    _description = 'Magento Sale Order Line'
    _inherits = {'sale.order.line': 'openerp_id'}

    _columns = {
        'magento_order_id': fields.many2one(
            'magento.sale.order', 'Magento Sale Order',
            required=True, ondelete='cascade',
            select=True),
        'magento_invoice_line_ids': fields.one2many(
                'magento.account.invoice.line', 'magento_order_line_id',
                string="Related invoice lines"),
        'openerp_id': fields.many2one('sale.order.line',
                                      string='Sale Order Line',
                                      required=True,
                                      ondelete='cascade'),
        }
        _sql_constraints = [
            ('magento_uniq', 'unique(backend_id, magento_id)',
             'A sale order line with the same ID on Magento already exists.'),
        ]
