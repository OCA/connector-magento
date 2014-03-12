# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: David BEAL Copyright 2014 Akretion
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

from openerp.osv import orm, fields
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime

from openerp.addons.connector.event import (
    on_record_write,
    on_record_create)
from openerp.addons.connector.unit.mapper import (
    mapping,
    ImportMapChild,
    ImportMapper,
    ExportMapper)
from openerp.addons.magentoerpconnect.unit.binder import MagentoModelBinder
import openerp.addons.magentoerpconnect.consumer as magentoerpconnect
from openerp.addons.magentoerpconnect.unit.backend_adapter import GenericAdapter
from openerp.addons.magentoerpconnect.backend import magento
from openerp.addons.magentoerpconnect.unit.export_synchronizer import MagentoExporter
from openerp.addons.magentoerpconnect import sale

import nltk


class MailMessage(orm.Model):
    _inherit = "mail.message"

    _columns = {
        'magento_sale_bind_ids': fields.one2many(
            'magento.sale.comment',
            'openerp_id',
            string="Magento Bindings"),
    }

    def is_customer_notified(self, cr, uid, sale_id, context=None):
        "'Magento store' define if customer must be notified"
        sale = self.pool['sale.order'].browse(cr, uid, sale_id, context=context)
        magento_store_id = self.pool['magento.store'].search(
            cr, uid, [('openerp_id', '=', sale.shop_id.id)], context=context)
        store = self.pool['magento.store'].browse(
            cr, uid, magento_store_id, context=context)[0]
        if store.send_sale_comment_mail is True:
            return True
        else:
            return False

    #def write(self, cr, uid, ids, vals, context=None):
    #    """Trigger a write on magento.sale.comment when mail.message
    #    are written to start synchro with magento comments"""
    #    if 'model' in vals and vals['model'] == 'sale.order':
    #        mag_sale_cmt_m = self.pool['magento.sale.comment']
    #        mag_cmt_ids = mag_sale_cmt_m.search(
    #            cr, uid, [('openerp_id', 'in', ids)], context=context)
    #        if mag_cmt_ids:
    #            values = {'sync_date': datetime.now().strftime(
    #                DEFAULT_SERVER_DATETIME_FORMAT)}
    #            mag_sale_cmt_m.write(
    #                cr, uid, mag_cmt_ids, values, context=context)
    #    return super(MailMessage, self).write(cr, uid, ids, vals, context=None)

    def create(self, cr, uid, vals, context=None):
        "Only message (not note) linked to sale.order must be send to Magento"
        message_id = super(MailMessage, self).create(
            cr, uid, vals, context=context)
        if vals.get('model') == 'sale.order' and vals.get('subtype_id'):
            mag_sale_m = self.pool['magento.sale.order']
            mag_sale_ids = mag_sale_m.search(
                cr, uid, [('openerp_id', '=', vals['res_id'])], context=context)
            if mag_sale_ids:
                mag_sales = mag_sale_m.browse(cr, uid, mag_sale_ids,
                                              context=context)
                for mag_sale in mag_sales:
                    values = {
                        'openerp_id': message_id,
                        'subject': _('Sent to Magento'),
                        'is_visible_on_front': True,
                        'is_customer_notified': self.is_customer_notified(
                            cr, uid, vals['res_id'], context=context),
                        'magento_sale_order_id': mag_sale.id,
                    }
                    self.pool['magento.sale.comment'].create(cr, uid, values,
                                                             context=context)
        return message_id


class MagentoSaleOrder(orm.Model):
    """Allow to have a relation between
    magento.sale.order and magento.sale.comment
    like you have a relation between
    magento.sale.order and magento.sale.order.line
    see in magentoerpconnect/sale.py
    """
    _inherit = 'magento.sale.order'

    _columns = {
        'magento_order_comment_ids': fields.one2many(
            'magento.sale.comment',
            'magento_sale_order_id',
            'Magento Sale comments'),
    }


class MagentoSaleComment(orm.Model):
    _name = 'magento.sale.comment'
    _inherit = 'magento.binding'
    _description = 'Magento Sale Comment'
    _inherits = {'mail.message': 'openerp_id'}

    MAGENTO_HELP = "This field is a technical / configuration field for the " \
                   "sale comment on Magento. \nPlease refer to the Magento " \
                   "documentation for details. "

    def _get_comments_from_order(self, cr, uid, ids, context=None):
        return self.pool['magento.sale.comment'].search(
            cr, uid, [('magento_sale_order_id', 'in', ids)], context=context)

    _columns = {
        'openerp_id': fields.many2one(
            'mail.message',
            string='Sale Comment',
            required=True,
            ondelete='cascade'),
        'magento_sale_order_id': fields.many2one(
            'magento.sale.order',
            'Magento Sale Order',
            required=True,
            ondelete='cascade',
            select=True),
        'is_customer_notified': fields.boolean(
            'Customer notified',
            help=MAGENTO_HELP),
        'is_visible_on_front': fields.boolean(
            'Visible on front',
            help=MAGENTO_HELP),
        'status': fields.char(
            'Order status',
            size=64,
            help=MAGENTO_HELP),
        'backend_id': fields.related(
            'magento_sale_order_id', 'backend_id',
            type='many2one',
            relation='magento.backend',
            string='Magento Backend',
            store={'magento.sale.comment': (lambda self, cr, uid, ids, c=None:
                                            ids, ['magento_sale_order_id'], 10),
                 'magento.sale.order':
                     (_get_comments_from_order, ['backend_id'], 20),
                   },
            readonly=True),
        'storeid': fields.char(
            'Store id',
            help=MAGENTO_HELP),
    }

    def create(self, cr, uid, vals, context=None):
        info = self.pool['magento.sale.order'].read(
            cr, uid, vals['magento_sale_order_id'], ['openerp_id'], context=context)
        if info:
            sale_id = info['openerp_id'][0]
            vals['res_id'] = sale_id
            vals['model'] = 'sale.order'
            if 'status' in vals:
                # subject customization
                options = []
                if vals.get('is_customer_notified'):
                    options.append(_('customer notified'))
                if vals.get('is_visible_on_front'):
                    options.append(_('visible on front'))
                option_string = ''
                if options:
                    option_string = '(' + ', ' . join(options) + ')'
                vals['subject'] = _('Magento comment in %s status %s') \
                    % (vals['status'], option_string)
        return super(MagentoSaleComment, self).create(cr, uid, vals,
                                                      context=context)


@magento(replacing=sale.SaleOrderCommentImportMapper)
class SaleOrderImportMapper(sale.SaleOrderCommentImportMapper):
    "Sales order has got an 'status_history' list which all magento comments"
    _model_name = 'magento.sale.order'

    children = sale.SaleOrderCommentImportMapper.children + [
        ('status_history',
         'magento_order_comment_ids',
         'magento.sale.comment')]


@magento
class SaleCommentImportMapper(ImportMapper):
    _model_name = 'magento.sale.comment'

    direct = [
        ('comment', 'body'),
        ('created_at', 'date'),
        ('status', 'status'),
    ]

    @mapping
    def type(self, record):
        return {'type': 'comment'}

    @mapping
    def store(self, record):
        if 'store_id' in record:
            return {'storeid': record['store_id']}

    @mapping
    def is_customer_notified(self, record):
        res = False
        if record['is_customer_notified'] == '1':
            res = True
        return {'is_customer_notified': res}

    @mapping
    def is_visible_on_front(self, record):
        res = False
        if record['is_visible_on_front'] == '1':
            res = True
        return {'is_visible_on_front': res}


@magento
class SaleCommentImportMapChild(ImportMapChild):
    _model_name = 'magento.sale.comment'

    def skip_item(self, map_record):
        if map_record.source['comment'] is None:
            return True


@magento(replacing=sale.SaleOrderImport)
class SaleOrderImport(sale.SaleOrderImport):
    _model_name = ['magento.sale.order']

    def _move_messages(self, binding):
        """magento messages from canceled (edit) order
        are moved to the new order"""
        mag_message_ids = self.session.search('magento.sale.comment', [
            ('model', '=', 'sale.order'),
            ('magento_sale_order_id', '!=', False),
            ('res_id', '=', binding.parent_id)])
        mag_sale_order_ids = self.session.search('magento.sale.order', [
            ('openerp_id', '=', binding.openerp_id.id)])
        vals = {
            'res_id': binding.openerp_id.id,
            'magento_id': False,
            'magento_sale_order_id': mag_sale_order_ids[0]}
        self.session.write('magento.sale.comment', mag_message_ids, vals)

    def _after_import(self, binding_id):
        super(SaleOrderImport, self)._after_import(binding_id)
        binding = self.session.browse(self.model._name, binding_id)
        if binding.magento_parent_id:
            'order has got a parent (the previous edit order)'
            self._move_messages(binding)


@magento
class SaleCommentAdapter(GenericAdapter):
    _model_name = 'magento.sale.comment'

    def create(self, order_increment, status, comment=None, notify=False):
        return self._call('sales_order.addComment',
                          [order_increment, status, comment, notify])


@magento
class MagentoSaleCommentBinder(MagentoModelBinder):
    _model_name = [
        'magento.sale.comment',
    ]


@magento
class MagentoSaleCommentExporter(MagentoExporter):
    """ Export sale order comments seller to Magento """
    _model_name = ['magento.sale.comment']

    def _should_import(self):
        return False

    def _create(self, data):
        """ Create the Magento record """
        # special check on data before export
        self._validate_data(data)   # you may inherit in your own module
        return self.backend_adapter.create(data['order_increment'],
                                           data['status'],
                                           data['comment'],
                                           data['notify'])


@magento
class SaleCommentExportMapper(ExportMapper):
    _model_name = 'magento.sale.comment'
    direct = [
        ('is_customer_notified', 'notify'),
    ]

    @mapping
    def comment(self, record):
        "clean html tags but keep break lines"
        comment = record.body
        for elm in ['</p>', '<br/>', '<br />', '<br>']:
            comment = comment.replace(elm, elm + '\n')
        return {'comment': nltk.clean_html(comment)}

    @mapping
    def status(self, record):
        state = record.magento_sale_order_id.openerp_id.state
        return {'status': sale.ORDER_STATUS_MAPPING.get(state, 'pending')}

    @mapping
    def order_increment(self, record):
        binder = self.get_binder_for_model('magento.sale.order')
        order_increment = binder.to_backend(
            record.magento_sale_order_id.id)
        return {'order_increment': order_increment}


@on_record_create(model_names=['magento.sale.comment'])
@on_record_write(model_names=['magento.sale.comment'])
def delay_export(session, model_name, record_id, vals):
    magentoerpconnect.delay_export(session, model_name, record_id, vals)
