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

from openerp import models, fields, api, _
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


class MailMessage(models.Model):
    _inherit = "mail.message"

    magento_sale_bind_ids = fields.One2many(
        'magento.sale.comment',
        'openerp_id',
        string="Magento Bindings")


@on_record_create(model_names='mail.message')
def create_mail_message(session, model_name, record_id, vals):
    if session.env.context.get('connector_no_export'):
        return
    if vals.get('model') == 'sale.order' and vals.get('subtype_id'):
        order = session.env['sale.order'].browse(vals['res_id'])
        for mag_sale in order.magento_bind_ids:
            store = mag_sale.storeview_id.store_id
            session.env['magento.sale.comment'].create({
                'openerp_id': record_id,
                'subject': _('Sent to Magento'),
                'is_visible_on_front': True,
                'is_customer_notified': store.send_sale_comment_mail,
                'magento_sale_order_id': mag_sale.id,
            })


class MagentoSaleOrder(models.Model):
    """Allow to have a relation between
    magento.sale.order and magento.sale.comment
    like you have a relation between
    magento.sale.order and magento.sale.order.line
    see in magentoerpconnect/sale.py
    """
    _inherit = 'magento.sale.order'

    magento_order_comment_ids = fields.One2many(
        'magento.sale.comment',
        'magento_sale_order_id',
        'Magento Sale comments')


class MagentoSaleComment(models.Model):
    _name = 'magento.sale.comment'
    _inherit = 'magento.binding'
    _description = 'Magento Sale Comment'
    _inherits = {'mail.message': 'openerp_id'}

    MAGENTO_HELP = "This field is a technical / configuration field for the " \
                   "sale comment on Magento. \nPlease refer to the Magento " \
                   "documentation for details. "

    openerp_id = fields.Many2one(
        'mail.message',
        string='Sale Comment',
        required=True,
        ondelete='cascade')
    magento_sale_order_id = fields.Many2one(
        'magento.sale.order',
        'Magento Sale Order',
        required=True,
        ondelete='cascade',
        select=True)
    is_customer_notified = fields.Boolean(
        'Customer notified',
        help=MAGENTO_HELP)
    is_visible_on_front = fields.Boolean(
        'Visible on front',
        help=MAGENTO_HELP)
    status = fields.Char(
        'Order status',
        size=64,
        help=MAGENTO_HELP)
    backend_id = fields.Many2one(
        'magento.backend', related='magento_sale_order_id.backend_id',
        string='Magento Backend',
        store=True,
        readonly=True)
    storeid = fields.Char(
        'Store id',
        help=MAGENTO_HELP)

    @api.model
    def create(self, vals):
        if 'res_id' not in vals:
            info = self.env['magento.sale.order'].browse(
                vals['magento_sale_order_id'])
            vals.update({
                'res_id': info.openerp_id.id,
                'model': 'sale.order',
                'backend_id': info.backend_id.id
            })
        return super(MagentoSaleComment, self).create(vals)


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
        mag_messages = self.session.env['magento.sale.comment'].search([
            ('model', '=', 'sale.order'),
            ('magento_sale_order_id', '!=', False),
            ('res_id', '=', binding.parent_id.id)])
        mag_sale_order = self.session.env['magento.sale.order'].search([
            ('openerp_id', '=', binding.openerp_id.id)
        ], limit=1)
        vals = {
            'res_id': binding.openerp_id.id,
            'magento_id': False,
            'magento_sale_order_id': mag_sale_order.id}
        mag_messages.write(vals)


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
        adapter = self.unit_for(
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
        binder = self.binder_for('magento.sale.order')
        order_increment = binder.to_backend(
            record.magento_sale_order_id.id)
        return {'order_increment': order_increment}


@on_record_create(model_names=['magento.sale.comment'])
@on_record_write(model_names=['magento.sale.comment'])
def delay_export(session, model_name, record_id, vals):
    magentoerpconnect.delay_export(session, model_name, record_id, vals)
