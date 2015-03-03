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
from openerp.addons.connector.event import (
    on_record_write,
    on_record_create)
from openerp.addons.connector.unit.mapper import (
    mapping,
    ImportMapChild,
    ImportMapper,
    ExportMapper)
from openerp.addons.magentoerpconnect.unit.binder import MagentoModelBinder
from openerp.addons.magentoerpconnect.unit.backend_adapter import (
    GenericAdapter,
)
import openerp.addons.magentoerpconnect.consumer as magentoerpconnect
from openerp.addons.magentoerpconnect.backend import magento
from openerp.addons.magentoerpconnect.unit.export_synchronizer import (
    MagentoExporter)
from openerp.addons.magentoerpconnect import sale

from bs4 import BeautifulSoup


class mail_message(orm.Model):
    _inherit = "mail.message"

    _columns = {
        'magento_sale_bind_ids': fields.one2many(
            'magento.sale.comment',
            'openerp_id',
            string="Magento Bindings"),
    }


@on_record_create(model_names='mail.message')
def create_mail_message(session, model_name, record_id, vals):
    if session.context.get('connector_no_export'):
        return
    if vals.get('model') == 'sale.order' and vals.get('subtype_id'):
        order = session.browse('sale.order', vals['res_id'])
        for mag_sale in order.magento_bind_ids:
            store = mag_sale.storeview_id.store_id
            session.create('magento.sale.comment', {
                'openerp_id': record_id,
                'subject': _('Sent to Magento'),
                'is_visible_on_front': True,
                'is_customer_notified': store.send_sale_comment_mail,
                'magento_sale_order_id': mag_sale.id,
            })


class magento_sale_order(orm.Model):
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


class magento_sale_comment(orm.Model):
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
            store={
                'magento.sale.comment': (
                    lambda self, cr, uid, ids, c=None:
                    ids,
                    ['magento_sale_order_id'],
                    10),
                'magento.sale.order': (
                    _get_comments_from_order,
                    ['backend_id'],
                    20),
                },
            readonly=True),
        'storeid': fields.char(
            'Store id',
            help=MAGENTO_HELP),
    }

    def create(self, cr, uid, vals, context=None):
        if 'res_id' not in vals:
            info = self.pool['magento.sale.order'].read(
                cr, uid, vals['magento_sale_order_id'],
                ['openerp_id'],
                context=context)
            vals.update({
                'res_id': info['openerp_id'][0],
                'model': 'sale.order',
                })
        return super(magento_sale_comment, self).create(
            cr, uid, vals, context=context)


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

    @mapping
    def subject(self, record):
        subject = _('Magento comment in %s status') % record['status']
        options = []
        if record.get('is_customer_notified'):
            options.append(_('customer notified'))
        if record.get('is_visible_on_front'):
            options.append(_('visible on front'))
        if options:
            subject += ' (' + ', ' . join(options) + ')'
        return {'subject': subject}


@magento
class SaleCommentImportMapChild(ImportMapChild):
    _model_name = 'magento.sale.comment'

    def skip_item(self, map_record):
        if map_record.source['comment'] is None:
            return True


@magento(replacing=sale.SaleOrderMoveComment)
class SaleOrderMoveComment(sale.SaleOrderMoveComment):
    _model_name = ['magento.sale.order']

    def move(self, binding):
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
        self._validate_create_data(data)   # you may inherit in your own module
        adapter = self.get_connector_unit_for_model(
            GenericAdapter,
            'magento.sale.order')
        return adapter.add_comment(data['order_increment'],
                                   data['status'],
                                   comment=data['comment'],
                                   notify=data['notify'])


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
        return {'comment': BeautifulSoup(comment).get_text()}

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
