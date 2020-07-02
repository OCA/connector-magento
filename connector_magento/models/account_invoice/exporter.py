# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging

import xmlrpc.client

from odoo import _
from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


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
        except xmlrpc.client.Fault as err:
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
