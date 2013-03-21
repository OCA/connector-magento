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
class MagentoPickingExport(ExportSynchronizer):
    _model_name = ['magento.stock.picking.out']

    def _get_args(self, picking, lines_info=None):
        if lines_info is None:
            lines_info = {}
        sale_binder = self.get_binder_for_model('magento.sale.order')
        magento_sale_id = sale_binder.to_backend(picking.magento_order_id.id)
        mail_notification = self._get_picking_mail_option(picking)
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
        item_qty = {}
        # get product and quantities to ship from the picking
        for line in picking.move_lines:
            sale_line = line.sale_line_id
            if not sale_line.magento_bind_ids:
                continue
            magento_sale_line = next((line for line in sale_line.magento_bind_ids
                                      if line.backend_id.id == picking.backend_id.id),
                                     None)
            if not magento_sale_line:
                continue
            item_id = magento_sale_line.magento_id
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

    def run(self, openerp_id):
        """
        Export the picking to Magento
        """
        picking = self.session.browse(self.model._name, openerp_id)
        picking_method = picking.picking_method
        if picking_method == 'complete':
            args = self._get_args(picking)
        elif picking_method == 'partial':
            lines_info = self._get_lines_info(picking)
            if not lines_info:
                raise NothingToDoJob(_('Canceled: the delivery order does not '
                                       'contain lines from the original sale order.'))
            args = self._get_args(picking, lines_info)
        else:
            raise ValueError("Wrong value for picking_method, authorized "
                             "values are 'partial' or 'complete', "
                             "found: %s" % picking_method)
        try:
            magento_id = self.backend_adapter.create(*args)
        except xmlrpclib.Fault as err:
            # When the shipping is already created on Magento, it returns:
            # <Fault 102: u"Impossible de faire l\'exp\xe9dition de la commande.">
            # In
            if err.faultCode == 102:
                raise NothingToDoJob('Canceled: the delivery order already '
                                     'exists on Magento (fault 102).')
            else:
                raise
        else:
            self.binder.bind(magento_id, openerp_id)


@magento
class MagentoTrackingExport(ExportSynchronizer):
    _model_name = ['magento.stock.picking.out']

    def _get_tracking_args(self, picking):
        return (picking.carrier_id.magento_carrier_code,
                picking.carrier_id.magento_tracking_title or '',
                picking.carrier_tracking_ref)

    def _validate(self, picking):
        if picking.state != 'done':  # should not happen
            raise ValueError("Wrong value for picking state, "
                             "it must be 'done', found: %s" % picking.state)
        if not picking.carrier_id.magento_carrier_code:
            raise FailedJobError("Wrong value for the Magento carrier code "
                                 "defined in the picking.")

    def _check_allowed_carrier(self, picking, magento_id):
        allowed_carriers = self.backend_adapter.get_carriers(magento_id)
        carrier = picking.carrier_id
        if carrier.magento_carrier_code not in allowed_carriers:
            raise FailedJobError("The carrier %(name)s does not accept "
                                 "tracking numbers on Magento.\n\n"
                                 "Tracking codes accepted by Magento:\n"
                                 "%(allowed)s.\n\n"
                                 "Actual tracking code:\n%(code)s\n\n"
                                 "Resolution:\n"
                                 "* Add support of %(code)s in Magento\n"
                                 "* Or deactivate the export of tracking "
                                 "numbers in the setup of the carrier %(name)s." %
                                 {'name': carrier.name,
                                  'allowed': allowed_carriers,
                                  'code': carrier.magento_carrier_code})

    def run(self, openerp_id):
        """ Export the tracking number of a picking to Magento """
        # verify the picking is done + magento id exists
        picking = self.session.browse(self.model._name, openerp_id)
        carrier = picking.carrier_id
        if not carrier:
            return FailedJobError('The carrier is missing on the picking %s.' %
                                  picking.name)

        if not carrier.magento_export_tracking:
            return _('The carrier %s does not export '
                     'tracking numbers.') % carrier.name
        if not picking.carrier_tracking_ref:
            return _('No tracking number to send.')

        magento_picking_id = picking.magento_id
        if magento_picking_id is None:
            raise NoExternalId("No value found for the picking ID on "
                               "Magento side, the job will be retried later.")

        self._validate(picking)
        self._check_allowed_carrier(picking, magento_picking_id)
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

    def run(self, openerp_id):
        """
        Run the job to export the paid invoice
        """
        sess = self.session
        invoice = sess.browse(self.model._name, openerp_id)

        magento_order = invoice.magento_order_id
        magento_stores = magento_order.shop_id.magento_bind_ids
        magento_store = next((store for store in magento_stores
                              if store.backend_id.id == invoice.backend_id.id),
                             None)
        assert magento_store
        mail_notification = magento_store.send_invoice_paid_mail

        lines_info = self._get_lines_info(invoice)
        # TODO: trap error 102 -> already created
        magento_id = self._export_invoice(magento_order.magento_id,
                                          lines_info,
                                          mail_notification)
        if magento_id:
            self.binder.bind(magento_id, openerp_id)


@job
def export_record(session, model_name, openerp_id, fields=None):
    """ Export a record on Magento """
    record = session.browse(model_name, openerp_id)
    env = get_environment(session, model_name, record.backend_id.id)
    exporter = env.get_connector_unit(MagentoExportSynchronizer)
    return exporter.run(openerp_id, fields=fields)


@job
def export_picking_done(session, model_name, record_id):
    """ Export a complete or partial delivery order. """
    picking = session.browse(model_name, record_id)
    backend_id = picking.backend_id.id
    env = get_environment(session, model_name, backend_id)
    picking_exporter = env.get_connector_unit(MagentoPickingExport)
    res = picking_exporter.run(record_id)

    if picking.carrier_tracking_ref:
        export_tracking_number.delay(session, model_name, record_id)
    return res


@job
def export_tracking_number(session, model_name, record_id):
    """ Export the tracking number of a delivery order. """
    picking = session.browse(model_name, record_id)
    backend_id = picking.backend_id.id
    env = get_environment(session, model_name, backend_id)
    tracking_exporter = env.get_connector_unit(MagentoTrackingExport)
    return tracking_exporter.run(record_id)


@job
def export_invoice_paid(session, model_name, record_id):
    """ Export a paid invoice. """
    invoice = session.browse(model_name, record_id)
    backend_id = invoice.backend_id.id
    env = get_environment(session, model_name, backend_id)
    invoice_exporter = env.get_connector_unit(MagentoInvoiceSynchronizer)
    return invoice_exporter.run(record_id)
