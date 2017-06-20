# -*- coding: utf-8 -*-
# © 2013 Guewen Baconnier,Camptocamp SA,Akretion
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import xmlrpclib
from odoo import api, models, fields, _
from odoo.addons.component.core import Component
from odoo.addons.queue_job.job import job, related_action
from odoo.addons.connector.exception import IDMissingInBackend

_logger = logging.getLogger(__name__)


class MagentoAccountInvoice(models.Model):
    """ Binding Model for the Magento Invoice """
    _name = 'magento.account.invoice'
    _inherit = 'magento.binding'
    _inherits = {'account.invoice': 'odoo_id'}
    _description = 'Magento Invoice'

    odoo_id = fields.Many2one(comodel_name='account.invoice',
                              string='Invoice',
                              required=True,
                              ondelete='cascade')
    magento_order_id = fields.Many2one(comodel_name='magento.sale.order',
                                       string='Magento Sale Order',
                                       ondelete='set null')

    _sql_constraints = [
        ('odoo_uniq', 'unique(backend_id, odoo_id)',
         'A Magento binding for this invoice already exists.'),
    ]

    @job(default_channel='root.magento')
    @related_action(action='related_action_unwrap_binding')
    @api.multi
    def export_invoice(self):
        """ Export a validated or paid invoice. """
        self.ensure_one()
        with self.backend_id.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            return exporter.run(self)


class AccountInvoice(models.Model):
    """ Adds the ``one2many`` relation to the Magento bindings
    (``magento_bind_ids``)
    """
    _inherit = 'account.invoice'

    magento_bind_ids = fields.One2many(
        comodel_name='magento.account.invoice',
        inverse_name='odoo_id',
        string='Magento Bindings',
    )


class AccountInvoiceAdapter(Component):
    """ Backend Adapter for the Magento Invoice """

    _name = 'magento.invoice.adapter'
    _inherit = 'magento.adapter'
    _apply_on = 'magento.account.invoice'

    _magento_model = 'sales_order_invoice'
    _admin_path = 'sales_invoice/view/invoice_id/{id}'

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

    def create(self, order_increment_id, items, comment, email,
               include_comment):
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


class MagentoInvoiceExporter(Component):
    """ Export invoices to Magento """
    _name = 'magento.account.invoice.exporter'
    _inherit = 'magento.exporter'
    _apply_on = ['magento.account.invoice']

    def _export_invoice(self, external_id, lines_info, mail_notification):
        if not lines_info:  # invoice without any line for the sale order
            return
        return self.backend_adapter.create(external_id,
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
        for line in invoice.invoice_line_ids:
            product = line.product_id
            # find the order line with the same product
            # and get the magento item_id (id of the line)
            # to invoice
            order_line = next((line for line in order.magento_order_line_ids
                               if line.product_id.id == product.id),
                              None)
            if order_line is None:
                continue

            item_id = order_line.external_id
            item_qty.setdefault(item_id, 0)
            item_qty[item_id] += line.quantity
        return item_qty

    def run(self, binding):
        """ Run the job to export the validated/paid invoice """

        magento_order = binding.magento_order_id
        magento_store = magento_order.store_id
        mail_notification = magento_store.send_invoice_paid_mail

        lines_info = self._get_lines_info(binding)
        external_id = None
        try:
            external_id = self._export_invoice(magento_order.external_id,
                                               lines_info,
                                               mail_notification)
        except xmlrpclib.Fault as err:
            # When the invoice is already created on Magento, it returns:
            # <Fault 102: 'Cannot do invoice for order.'>
            # We'll search the Magento invoice ID to store it in Odoo
            if err.faultCode == 102:
                _logger.debug('Invoice already exists on Magento for '
                              'sale order with magento id %s, trying to find '
                              'the invoice id.',
                              magento_order.external_id)
                external_id = self._get_existing_invoice(magento_order)
                if external_id is None:
                    # In that case, we let the exception bubble up so
                    # the user is informed of the 102 error.
                    # We couldn't find the invoice supposedly existing
                    # so an investigation may be necessary.
                    raise
            else:
                raise
        # When the invoice already exists on Magento, it may return
        # a 102 error (handled above) or return silently without ID
        if not external_id:
            # If Magento returned no ID, try to find the Magento
            # invoice, but if we don't find it, let consider the job
            # as done, because Magento did not raised an error
            external_id = self._get_existing_invoice(magento_order)

        if external_id:
            self.binder.bind(external_id, binding.id)

    def _get_existing_invoice(self, magento_order):
        invoices = self.backend_adapter.search_read(
            order_id=magento_order.magento_order_id)
        if not invoices:
            return
        if len(invoices) > 1:
            return
        return invoices[0]['increment_id']


class MagentoBindingInvoiceListener(Component):
    _name = 'magento.binding.account.invoice.listener'
    _inherit = 'base.event.listener'
    _apply_on = ['magento.account.invoice']

    def on_record_create(self, record, fields=None):
        record.with_delay().export_invoice()


class MagentoInvoiceListener(Component):
    _name = 'magento.account.invoice.listener'
    _inherit = 'base.event.listener'
    _apply_on = ['account.invoice']

    def on_invoice_paid(self, record):
        self.invoice_create_bindings(record)

    def on_invoice_validated(self, record):
        self.invoice_create_bindings(record)

    def invoice_create_bindings(self, invoice):
        """
        Create a ``magento.account.invoice`` record. This record will then
        be exported to Magento.
        """
        # find the magento store to retrieve the backend
        # we use the shop as many sale orders can be related to an invoice
        sales = invoice.mapped('invoice_line_ids.sale_line_ids.order_id')
        for sale in sales:
            for magento_sale in sale.magento_bind_ids:
                binding_exists = False
                for mag_inv in invoice.magento_bind_ids:
                    if mag_inv.backend_id.id == magento_sale.backend_id.id:
                        binding_exists = True
                        break
                if binding_exists:
                    continue
                # Check if invoice state matches configuration setting
                # for when to export an invoice
                magento_store = magento_sale.store_id
                payment_method = sale.payment_mode_id
                if payment_method and payment_method.create_invoice_on:
                    create_invoice = payment_method.create_invoice_on
                else:
                    create_invoice = magento_store.create_invoice_on

                if create_invoice == invoice.state:
                    self.env['magento.account.invoice'].create({
                        'backend_id': magento_sale.backend_id.id,
                        'odoo_id': invoice.id,
                        'magento_order_id': magento_sale.id})
