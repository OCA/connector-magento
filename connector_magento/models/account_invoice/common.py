# Copyright 2013-2019 Camptocamp SA
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging
import xmlrpc.client
from odoo import api, models, fields
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
    def export_record(self):
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
    # Not valid without security key
    # _admin2_path = 'sales/order_invoice/view/invoice_id/{id}'

    def _call(self, method, arguments, http_method=None):
        try:
            return super(AccountInvoiceAdapter, self)._call(
                method, arguments, http_method=http_method)
        except xmlrpc.client.Fault as err:
            # this is the error in the Magento API
            # when the invoice does not exist
            if err.faultCode == 100:
                raise IDMissingInBackend
            else:
                raise

    def create(self, order_increment_id, items, comment, email,
               include_comment):
        """ Create a record on the external system """
        # pylint: disable=method-required-super
        if self.collection.version == '1.7':
            return self._call('%s.create' % self._magento_model,
                              [order_increment_id, items, comment,
                               email, include_comment])

        # Compose payload for Magento 2.x
        arguments = {
            'capture': False,
            'items': [{'orderItemId': key, 'qty': value}
                      for key, value in items.items()],
            'comment': {
                'comment': comment,
                'isVisibleOnFront': 0,
                },
            'appendComment': include_comment,
        }
        return self._call(
            'order/%s/invoice' % order_increment_id, arguments,
            http_method='post')

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


class MagentoBindingInvoiceListener(Component):
    _name = 'magento.binding.account.invoice.listener'
    _inherit = 'base.event.listener'
    _apply_on = ['magento.account.invoice']

    def on_record_create(self, record, fields=None):
        record.with_delay().export_record()


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
                payment_mode = sale.payment_mode_id
                if payment_mode and payment_mode.create_invoice_on:
                    create_invoice = payment_mode.create_invoice_on
                else:
                    create_invoice = magento_store.create_invoice_on

                if create_invoice == invoice.state:
                    self.env['magento.account.invoice'].create({
                        'backend_id': magento_sale.backend_id.id,
                        'odoo_id': invoice.id,
                        'magento_order_id': magento_sale.id})
