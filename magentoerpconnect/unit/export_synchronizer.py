# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
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
from openerp.tools.translate import _
import openerp.addons.connector as connector
from openerp.addons.connector.queue.job import job
from openerp.addons.connector.unit.synchronizer import ExportSynchronizer
from openerp.addons.connector.exception import (
        FailedJobError,
        NoExternalId,
        NothingToDoJob)
from openerp.addons.connector_ecommerce.event import on_tracking_number_added
from ..backend import magento
from ..connector import get_environment

_logger = logging.getLogger(__name__)


class MagentoExportSynchronizer(ExportSynchronizer):
    """ Base exporter for Magento """

    def __init__(self, environment):
        """
        :param environment: current environment (backend, session, ...)
        :type environment: :py:class:`connector.connector.Environment`
        """
        super(MagentoExportSynchronizer, self).__init__(environment)
        self.openerp_id = None
        self.openerp_record = None

    def _get_openerp_data(self):
        """ Return the raw OpenERP data for ``self.openerp_id`` """
        cr, uid, context = (self.session.cr,
                            self.session.uid,
                            self.session.context)
        return self.model.browse(cr, uid, self.openerp_id, context=context)

    def _has_to_skip(self):
        """ Return True if the import can be skipped """
        return False

    def _export_dependencies(self):
        """ Export the dependencies for the record"""
        return

    def _map_data(self, fields=None):
        """ Return the external record converted to OpenERP """
        return self.mapper.convert(self.openerp_record, fields=fields)

    def _validate_data(self, data):
        """ Check if the values to import are correct

        Pro-actively check before the ``Model.create`` or
        ``Model.update`` if some fields are missing

        Raise `InvalidDataError`
        """
        return

    def _create(self, data):
        """ Create the Magento record """
        magento_id = self.backend_adapter.create(data)
        return magento_id

    def _update(self, magento_id, data):
        """ Update an Magento record """
        self.backend_adapter.write(magento_id, data)

    def run(self, openerp_id, fields=None):
        """ Run the synchronization

        :param openerp_id: identifier of the record
        """
        self.openerp_id = openerp_id
        self.openerp_record = self._get_openerp_data()

        magento_id = self.binder.to_backend(self.openerp_id)
        if not magento_id:
            fields = None  # should be created with all the fields

        if self._has_to_skip():
            return

        # import the missing linked resources
        self._export_dependencies()

        record = self._map_data(fields=fields)
        if not record:
            raise connector.exception.NothingToDoJob

        # special check on data before import
        self._validate_data(record)

        if magento_id:
            # FIXME magento record could have been deleted,
            # we would need to create the record
            # (with all fields)
            self._update(magento_id, record)
        else:
            magento_id = self._create(record)

        self.binder.bind(magento_id, self.openerp_id)
        # TODO: check if strings are translated, fear that they aren't
        return _('Record exported with ID %s on Magento.') % magento_id


@magento
class PartnerExport(MagentoExportSynchronizer):
    _model_name = ['magento.res.partner']


@magento
class MagentoPickingExport(ExportSynchronizer):
    _model_name = ['magento.stock.picking']

    def _get_args(self, magento_sale_id,
                  mail_notification=False, lines_info=None):
        if lines_info is None:
            lines_info = {}
        return (magento_sale_id, lines_info,
                _("Shipping Created"), mail_notification, True)

    def _get_lines_info(self, picking):
        """
        Get the line to export to Magento. In case some lines doesn't have a
        matching on Magento, we ignore them. This allow to add lines manually.

        :param picking: picking is a record of a stock.picking
        :type picking: browse_record
        :return: dict of {magento_product_id: quantity}
        :rtype: dict
        """
        order_line_binder = self.get_binder_for_model('magento.sale.order.line')
        item_qty = {}
        # get product and quantities to ship from the picking
        for line in picking.move_lines:
            item_id = order_line_binder.to_backend(line.sale_line_id.id)
            if item_id:
                item_qty.setdefault(item_id, 0)
                item_qty[item_id] += line.product_qty
        return item_qty

    def _get_picking_mail_option(self, picking):
        """

        :param picking: picking is an instance of a stock.picking browse record
        :type picking: browse_record
        :returns: value of send_picking_done_mail chosen on magento shop
        :rtype: boolean
        """
        magento_shop = picking.sale_id.shop_id.magento_bind_ids[0]
        return magento_shop.send_picking_done_mail

    def run(self, openerp_id, picking_type):
        """
        Run the job to export the picking with args to ask for partial or
        complete picking.

        :param picking_type: picking_type, can be 'complete' or 'partial'
        :type picking_type: str
        """
        picking = self.session.browse(self.model._name, openerp_id)
        binder = self.get_binder_for_model('magento.sale.order')
        magento_sale_id = binder.to_backend(picking.magento_order_id.id)
        mail_notification = self._get_picking_mail_option(picking)
        if picking_type == 'complete':
            args = self._get_args(magento_sale_id, mail_notification)
        elif picking_type == 'partial':
            lines_info = self._get_lines_info(picking)
            args = self._get_args(magento_sale_id,
                                  mail_notification,
                                  lines_info)
        else:
            raise ValueError("Wrong value for picking_type, authorized "
                             "values are 'partial' or 'complete', "
                             "found: %s" % picking_type)
        try:
            magento_id = self.backend_adapter.create(*args)
        except xmlrpclib.Fault as err:
            # When the shipping is already created on Magento, it returns:
            # <Fault 102: u"Impossible de faire l\'exp\xe9dition de la commande.">
            # In
            if err.faultCode == 102:
                raise NothingToDoJob
            else:
                raise
        else:
            self.binder.bind(magento_id, openerp_id)


@magento
class MagentoTrackingExport(ExportSynchronizer):
    _model_name = ['magento.stock.picking']

    def _get_tracking_args(self, picking, tracking_number):
        return (picking.carrier_id.magento_carrier_code,
                picking.carrier_id.magento_tracking_title or '',
                packing.carrier_tracking_ref)

    def _validate(self, picking):
        # should not happen: event fired only after 'done'
        if picking.state != 'done':
            raise ValueError("Wrong value for picking state, "
                             "it must be 'done', found: %s" % picking.state)
        if not picking.carrier_id:
            raise FailedJobError("No carrier selected on the picking, "
                             "it must be defined.")
        if not picking.carrier_id.magento_carrier_code:
            raise FailedJobError("Wrong value for the Magento carrier code "
                                 "defined in the picking.")

    def run(self, openerp_id):
        """ Export the tracking number of a picking to Magento """
        # verify the picking is done + magento id exists
        picking = self.session.browse('stock.picking', openerp_id)
        if not picking.tracking_number:
            return _('No tracking number to send.')

        binder = self.get_binder_for_model('magento.stock.picking')
        magento_picking_id = binder.to_backend(picking.id)
        if magento_picking_id is None:
            raise NoExternalId("No value found for the picking ID on "
                               "Magento side, the job will be retried later.")

        self._validate(picking)
        tracking_args = self._get_tracking_args(picking)
        self.backend_adapter.add_tracking_number(magento_picking_id,
                                                 *tracking_args)


@magento
class MagentoInvoiceSynchronizer(ExportSynchronizer):
    _model_name = ['magento.account.invoice']

    def _export_invoice(self, magento_id, lines_info, mail_notification):
        # TODO
        # WARNING: Think of the case that invoice exits..  => Add try
        # except on the right exception. This is to handle the case that
        # the invoice is already created. So the task is considered as
        # done !
        self.backend_adapter.create((magento_id, lines_info,
                                    _("Invoice Created"), mail_notification,
                                    False))

    def _get_lines_info(self, invoice):
        """
        Get the line to export to Magento. In case some lines doesn't have a
        matching on Magento, we ignore them. This allow to add lines manually.

        :param invoice: invoice is an account.invoice record
        :type invoice: browse_record
        :return: dict of {magento_product_id: quantity}
        :rtype: dict
        """
        order_line_binder = self.get_binder_for_model('magento.sale.order.line')
        item_qty = {}
        # get product and quantities to invoice
        # if no magento id found, do not export it
        for line in invoice.invoice_line:
            if not line.magento_order_line_id:
                continue
            order_line_id = line.magento_order_line_id.openerp_id.id
            item_id = order_line_binder.to_backend(order_line_id)
            item_qty.setdefault(item_id, 0)
            item_qty[item_id] += line.product_qty
        return item_qty

    def run(self, openerp_id):
        """
        Run the job to export the paid invoice
        """
        invoice = self.session.browse('account.invoice', openerp_id)
        order = invoice.sale_order_ids
        if len(order) != 1:
            raise ValueError("Wrong value for sale_order_ids, "
                             "you must have only one sale order "
                             "related to the invoice in order to export it.")
        order = order[0]
        binder = self.get_binder_for_model('magento.sale.order')
        magento_so_id = binder.to_backend(order.id)
        mail_notification = order.shop_id.send_invoice_paid_mail

        balance = order.amount_total - invoice.amount_total
        precision = self.session.pool.get('decimal.precision').precision_get(
                self.session.cr, self.session.uid, 'Account')
        lines_info = self._get_lines_info(invoice)
        self._export_invoice(magento_so_id, lines_info, mail_notification)


@job
def export_record(session, model_name, openerp_id, fields=None):
    """ Export a record on Magento """
    model = session.pool.get(model_name)
    record = model.browse(session.cr, session.uid, openerp_id,
                          context=session.context)
    env = get_environment(session, model_name, record.backend_id.id)
    exporter = env.get_connector_unit(MagentoExportSynchronizer)
    return exporter.run(openerp_id, fields=fields)


@job
def export_picking_done(session, model_name, backend_id, record_id, picking_type):
    """ Export a complete or partial delivery order. """
    # TODO: job's description is the docstring currently. Could we take
    # only the first paragraph or move the description to a decorator?
    """
    :param picking_type: picking_type, can be 'complete' or 'partial'
        :type picking_type: str
    """
    env = get_environment(session, 'magento.stock.picking', backend_id)
    picking_exporter = env.get_connector_unit(MagentoPickingExport)
    res = picking_exporter.run(record_id, picking_type)

    picking = session.browse(model_name, record_id)
    if picking.carrier_tracking_ref:
        export_tracking_number.delay(session, model_name, backend_id, record_id)
    return res


@job
def export_tracking_number(session, model_name, backend_id, record_id):
    """ Export the tracking number of a delivery order. """
    env = get_environment(session, model_name, backend_id)
    tracking_exporter = env.get_connector_unit(MagentoTrackingExport)
    return tracking_exporter.run(record_id)


@job
def export_invoice_paid(session, model_name, backend_id, record_id):
    """ Export a paid invoice. """
    env = get_environment(session, model_name, backend_id)
    invoice_exporter = env.get_connector_unit(MagentoInvoiceSynchronizer)
    return invoice_exporter.run(record_id)
