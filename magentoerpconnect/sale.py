# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Joel Grand-Guillaume
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
import openerp.addons.decimal_precision as dp


ORDER_STATUS_MAPPING = {  # XXX check if still needed
    'manual': 'processing',
    'progress': 'processing',
    'shipping_except': 'complete',
    'invoice_except': 'complete',
    'done': 'complete',
    'cancel': 'canceled',
    'waiting_date': 'holded'}


class magento_sale_order(orm.Model):
    _name = 'magento.sale.order'
    _inherit = 'magento.binding'
    _description = 'Magento Sale Order'
    _inherits = {'sale.order': 'openerp_id'}

    _columns = {
        'openerp_id': fields.many2one('sale.order',
                                      string='Sale Order',
                                      required=True,
                                      ondelete='cascade'),
        'magento_order_lines': fields.one2many('magento.sale.order.line', 'magento_order_id',
                                               'Magento Order Lines'),
        'total_amount': fields.float('Total amount',
                                     digits_compute=dp.get_precision('Account')), # XXX common to all ecom sale orders
        'total_amount_tax': fields.float('Total amount w. tax',
                                         digits_compute=dp.get_precision('Account')), # XXX common to all ecom sale orders
        }

    _sql_constraints = [
        ('magento_uniq', 'unique(backend_id, magento_id)',
         'A sale order line with the same ID on Magento already exists.'),
    ]


class sale_order(orm.Model):
    _inherit = 'sale.order'

    _columns = {
            'magento_bind_ids': fields.one2many(
                'magento.sale.order', 'openerp_id',
                string="Magento Bindings"),
        }


class magento_sale_order_line(orm.Model):
    _name = 'magento.sale.order.line'
    _inherit = 'magento.binding'
    _description = 'Magento Sale Order Line'
    _inherits = {'sale.order.line': 'openerp_id'}


    def _get_lines_from_order(self, cr, uid, ids, context=None):
        line_obj = self.pool.get('magento.sale.order.line')
        return line_obj.search(cr, uid,
                               [('magento_order_id', 'in', ids)],
                               context=context)
    _columns = {
        ## 'order_id': fields.related('magento_order_id', 'openerp_id',
        ##                            type='many2one',
        ##                            relation='sale.order',
        ##                            string='Sale Order',
        ##                            readonly=True,
        ##                            store=True),
        'magento_order_id': fields.many2one('magento.sale.order', 'Magento Sale Order',
                                            required=True,
                                            ondelete='cascade',
                                            select=True),
        'magento_invoice_line_ids': fields.one2many(
                'magento.account.invoice.line', 'magento_order_line_id',
                string="Related invoice lines"),
        'openerp_id': fields.many2one('sale.order.line',
                                      string='Sale Order Line',
                                      required=True,
                                      ondelete='cascade'),
        'backend_id': fields.related(
            'magento_order_id', 'backend_id',
             type='many2one',
             relation='magento.backend',
             string='Magento Backend',
             store={'magento.sale.order.line':
                        (lambda self, cr, uid, ids, c=None: ids,
                         ['magento_order_id'],
                         10),
                 'magento.sale.order':
                     (_get_lines_from_order, ['backend_id'], 20),
                   },
             readonly=True),
        'tax_rate': fields.float('Tax Rate',
                                 digits_compute=dp.get_precision('Account')),
        'notes': fields.char('Notes'), # XXX common to all ecom sale orders
        }

    _sql_constraints = [
        ('magento_uniq', 'unique(backend_id, magento_id)',
         'A sale order line with the same ID on Magento already exists.'),
    ]

    def create(self, cr, uid, vals, context=None):
        magento_order_id = vals['magento_order_id']
        info = self.pool['magento.sale.order'].read(cr, uid,
                                                    [magento_order_id],
                                                    ['openerp_id'],
                                                    context=context)
        order_id = info[0]['openerp_id']
        vals['order_id'] = order_id[0]
        super(magento_sale_order_line, self).create(cr, uid, vals, context)


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
