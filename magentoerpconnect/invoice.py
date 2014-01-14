# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Joël Grand-Guillaume, Guewen Baconnier
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

import logging
import xmlrpclib
from openerp.osv import fields, orm
from openerp.tools.translate import _
from openerp.addons.connector.queue.job import job
from openerp.addons.connector.unit.synchronizer import ExportSynchronizer
from openerp.addons.connector.event import on_record_create
from openerp.addons.connector_ecommerce.event import (on_invoice_paid,
                                                      on_invoice_validated)
from openerp.addons.connector.exception import IDMissingInBackend
from .unit.backend_adapter import GenericAdapter
from .connector import get_environment
from .backend import magento

_logger = logging.getLogger(__name__)


class magento_account_invoice(orm.Model):
    """ Binding Model for the Magento Invoice """
    _name = 'magento.account.invoice'
    _inherit = 'magento.binding'
    _inherits = {'account.invoice': 'openerp_id'}
    _description = 'Magento Invoice'

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
    """ Adds the ``one2many`` relation to the Magento bindings
    (``magento_bind_ids``)"""
    _inherit = 'account.invoice'

    _columns = {
        'magento_bind_ids': fields.one2many(
            'magento.account.invoice', 'openerp_id',
            string="Magento Bindings"),
    }

    def copy_data(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default['magento_bind_ids'] = False
        return super(account_invoice, self).copy_data(cr, uid, id,
                                                      default=default,
                                                      context=context)


@magento
class AccountInvoiceAdapter(GenericAdapter):
    """ Backend Adapter for the Magento Invoice """
    _model_name = 'magento.account.invoice'
    _magento_model = 'sales_order_invoice'

    def _call(self, method, arguments):
        try:
            return super(AccountInvoiceAdapter, self)._call(method, arguments)
        except xmlrpclib.Fault as err:
            # this is the error in the Magento API
            # when the invoice does not exist
            if err.faultCode == 100:
                raise IDMissingInBackend
            else:
                raise

    def create(self, order_increment_id, items, comment, email, include_comment):
        """ Create a record on the external system """
        return self._call('%s.create' % self._magento_model,
                          [order_increment_id, items, comment,
                           email, include_comment])

    def search_read(self, filters=None, order_id=None):
        """ Search records according to some criterias
        and returns their information

        :param order_id: 'order_id' field of the magento sale order, this
                         is not the same field than 'increment_id'
        """
        if filters is None:
            filters = {}
        if order_id is not None:
            filters['order_id'] = {'eq': order_id}
        return super(AccountInvoiceAdapter, self).search_read(filters=filters)


@magento
class MagentoInvoiceSynchronizer(ExportSynchronizer):
    """ Export invoices to Magento """
    _model_name = ['magento.account.invoice']

    def _export_invoice(self, magento_id, lines_info, mail_notification):
        if not lines_info:  # invoice without any line for the sale order
            return
        return self.backend_adapter.create(magento_id,
                                           lines_info,
                                           _("Invoice Created"),
                                           mail_notification,
                                           False)

    def _get_lines_info(self, invoice):
        """
        Get the line to export to Magento. In case some lines doesn't have a
        matching on Magento, we ignore them. This allow to add lines manually.

        :param invoice: invoice is an magento.account.invoice record
        :type invoice: browse_record
        :return: dict of {magento_product_id: quantity}
        :rtype: dict
        """
        item_qty = {}
        # get product and quantities to invoice
        # if no magento id found, do not export it
        order = invoice.magento_order_id
        for line in invoice.invoice_line:
            product = line.product_id
            # find the order line with the same product
            # and get the magento item_id (id of the line)
            # to invoice
            order_line = next((line for line in order.magento_order_line_ids
                               if line.product_id.id == product.id),
                              None)
            if order_line is None:
                continue

            item_id = order_line.magento_id
            item_qty.setdefault(item_id, 0)
            item_qty[item_id] += line.quantity
        return item_qty

    def run(self, binding_id):
        """ Run the job to export the validated/paid invoice """
        sess = self.session
        invoice = sess.browse(self.model._name, binding_id)

        magento_order = invoice.magento_order_id
        magento_stores = magento_order.shop_id.magento_bind_ids
        magento_store = next((store for store in magento_stores
                              if store.backend_id.id == invoice.backend_id.id),
                             None)
        assert magento_store
        mail_notification = magento_store.send_invoice_paid_mail

        lines_info = self._get_lines_info(invoice)
        try:
            magento_id = self._export_invoice(magento_order.magento_id,
                                              lines_info,
                                              mail_notification)
        except xmlrpclib.Fault as err:
            # When the invoice is already created on Magento, it returns:
            # <Fault 102: 'Cannot do invoice for order.'>
            # We'll search the Magento invoice ID to store it in OpenERP
            if err.faultCode == 102:
                _logger.debug('Invoice already exists on Magento for '
                              'sale order with magento id %s, trying to find '
                              'the invoice id.',
                              magento_order.magento_id)
                magento_id = self._get_existing_invoice(magento_order)
            else:
                raise

        self.binder.bind(magento_id, binding_id)

    def _get_existing_invoice(self, magento_order):
        invoices = self.backend_adapter.search_read(
                order_id=magento_order.magento_order_id)
        if not invoices:
            raise
        if len(invoices) > 1:
            raise
        return invoices[0]['increment_id']


@on_invoice_validated
@on_invoice_paid
def invoice_create_bindings(session, model_name, record_id):
    """
    Create a ``magento.account.invoice`` record. This record will then
    be exported to Magento.
    """
    invoice = session.browse(model_name, record_id)
    # find the magento store to retrieve the backend
    # we use the shop as many sale orders can be related to an invoice
    for sale in invoice.sale_ids:
        for magento_sale in sale.magento_bind_ids:
            # Check if invoice state matches configuration setting
            # for when to export an invoice
            magento_stores = magento_sale.shop_id.magento_bind_ids
            magento_store = next((store for store in magento_stores
                                  if store.backend_id.id == magento_sale.backend_id.id),
                                 None)
            assert magento_store
            create_invoice = magento_store.create_invoice_on

            if create_invoice == invoice.state:
                session.create('magento.account.invoice',
                               {'backend_id': magento_sale.backend_id.id,
                                'openerp_id': invoice.id,
                                'magento_order_id': magento_sale.id})


@on_record_create(model_names='magento.account.invoice')
def delay_export_account_invoice(session, model_name, record_id, vals):
    """
    Delay the job to export the magento invoice.
    """
    export_invoice.delay(session, model_name, record_id)


@job
def export_invoice_paid(session, model_name, record_id):
    """ Deprecated in 2.1.0.dev0. """
    _logger.warning('Deprecated: the export_invoice_paid() job is deprecated '
                    'in favor of export_invoice()')
    return export_invoice(session, model_name, record_id)


@job
def export_invoice(session, model_name, record_id):
    """ Export a validated or paid invoice. """
    invoice = session.browse(model_name, record_id)
    backend_id = invoice.backend_id.id
    env = get_environment(session, model_name, backend_id)
    invoice_exporter = env.get_connector_unit(MagentoInvoiceSynchronizer)
    return invoice_exporter.run(record_id)
