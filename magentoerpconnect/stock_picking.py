# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Joël Grand-Guillaume
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
from openerp import models, fields
from openerp.tools.translate import _
from openerp.addons.connector.queue.job import job, related_action
from openerp.addons.connector.event import on_record_create
from openerp.addons.connector.exception import NothingToDoJob
from openerp.addons.connector.unit.synchronizer import Exporter
from openerp.addons.connector.exception import IDMissingInBackend
from openerp.addons.connector_ecommerce.event import on_picking_out_done
from .unit.backend_adapter import GenericAdapter
from .connector import get_environment
from .backend import magento
from .stock_tracking import export_tracking_number
from .related_action import unwrap_binding

_logger = logging.getLogger(__name__)


class MagentoStockPicking(models.Model):
    _name = 'magento.stock.picking'
    _inherit = 'magento.binding'
    _inherits = {'stock.picking': 'openerp_id'}
    _description = 'Magento Delivery Order'

    openerp_id = fields.Many2one(comodel_name='stock.picking',
                                 string='Stock Picking',
                                 required=True,
                                 ondelete='cascade')
    magento_order_id = fields.Many2one(comodel_name='magento.sale.order',
                                       string='Magento Sale Order',
                                       ondelete='set null')
    picking_method = fields.Selection(selection=[('complete', 'Complete'),
                                                 ('partial', 'Partial')],
                                      string='Picking Method',
                                      required=True)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    magento_bind_ids = fields.One2many(
        comodel_name='magento.stock.picking',
        inverse_name='openerp_id',
        string="Magento Bindings",
    )


@magento
class StockPickingAdapter(GenericAdapter):
    _model_name = 'magento.stock.picking'
    _magento_model = 'sales_order_shipment'
    _admin_path = 'sales_shipment/view/shipment_id/{id}'

    def _call(self, method, arguments):
        try:
            return super(StockPickingAdapter, self)._call(method, arguments)
        except xmlrpclib.Fault as err:
            # this is the error in the Magento API
            # when the shipment does not exist
            if err.faultCode == 100:
                raise IDMissingInBackend
            else:
                raise

    def create(self, order_id, items, comment, email, include_comment):
        """ Create a record on the external system """
        return self._call('%s.create' % self._magento_model,
                          [order_id, items, comment, email, include_comment])

    def add_tracking_number(self, magento_id, carrier_code,
                            tracking_title, tracking_number):
        """ Add new tracking number.

        :param magento_id: shipment increment id
        :param carrier_code: code of the carrier on Magento
        :param tracking_title: title displayed on Magento for the tracking
        :param tracking_number: tracking number
        """
        return self._call('%s.addTrack' % self._magento_model,
                          [magento_id, carrier_code,
                           tracking_title, tracking_number])

    def get_carriers(self, magento_id):
        """ Get the list of carrier codes allowed for the shipping.

        :param magento_id: order increment id
        :rtype: list
        """
        return self._call('%s.getCarriers' % self._magento_model,
                          [magento_id])


@magento
class MagentoPickingExporter(Exporter):
    _model_name = ['magento.stock.picking']

    def _get_args(self, picking, lines_info=None):
        if lines_info is None:
            lines_info = {}
        sale_binder = self.binder_for('magento.sale.order')
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
            sale_line = line.procurement_id.sale_line_id
            if not sale_line.magento_bind_ids:
                continue
            magento_sale_line = next(
                (line for line in sale_line.magento_bind_ids
                 if line.backend_id.id == picking.backend_id.id),
                None
            )
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
        magento_shop = picking.sale_id.magento_bind_ids[0].store_id
        return magento_shop.send_picking_done_mail

    def run(self, binding_id):
        """
        Export the picking to Magento
        """
        picking = self.model.browse(binding_id)
        if picking.magento_id:
            return _('Already exported')
        picking_method = picking.picking_method
        if picking_method == 'complete':
            args = self._get_args(picking)
        elif picking_method == 'partial':
            lines_info = self._get_lines_info(picking)
            if not lines_info:
                raise NothingToDoJob(_('Canceled: the delivery order does not '
                                       'contain lines from the original '
                                       'sale order.'))
            args = self._get_args(picking, lines_info)
        else:
            raise ValueError("Wrong value for picking_method, authorized "
                             "values are 'partial' or 'complete', "
                             "found: %s" % picking_method)
        try:
            magento_id = self.backend_adapter.create(*args)
        except xmlrpclib.Fault as err:
            # When the shipping is already created on Magento, it returns:
            # <Fault 102: u"Impossible de faire
            # l\'exp\xe9dition de la commande.">
            if err.faultCode == 102:
                raise NothingToDoJob('Canceled: the delivery order already '
                                     'exists on Magento (fault 102).')
            else:
                raise
        else:
            self.binder.bind(magento_id, binding_id)
            # ensure that we store the external ID
            self.session.commit()


MagentoPickingExport = MagentoPickingExporter  # deprecated


@on_picking_out_done
def picking_out_done(session, model_name, record_id, picking_method):
    """
    Create a ``magento.stock.picking`` record. This record will then
    be exported to Magento.

    :param picking_method: picking_method, can be 'complete' or 'partial'
    :type picking_method: str
    """
    picking = session.env[model_name].browse(record_id)
    sale = picking.sale_id
    if not sale:
        return
    for magento_sale in sale.magento_bind_ids:
        session.env['magento.stock.picking'].create({
            'backend_id': magento_sale.backend_id.id,
            'openerp_id': picking.id,
            'magento_order_id': magento_sale.id,
            'picking_method': picking_method})


@on_record_create(model_names='magento.stock.picking')
def delay_export_picking_out(session, model_name, record_id, vals):
    binding = session.env[model_name].browse(record_id)
    # tracking number is sent when:
    # * the picking is exported and the tracking number was already
    #   there before the picking was done OR
    # * the tracking number is added after the picking is done
    # We have to keep the initial state of whether we had an
    # tracking number in the job kwargs, because if we read the
    # picking at the time of execution of the job, a tracking could
    # have been added and it would be exported twice.
    with_tracking = bool(binding.carrier_tracking_ref)
    export_picking_done.delay(session, model_name, record_id,
                              with_tracking=with_tracking)


@job(default_channel='root.magento')
@related_action(action=unwrap_binding)
def export_picking_done(session, model_name, record_id, with_tracking=True):
    """ Export a complete or partial delivery order. """
    # with_tracking is True to keep a backward compatibility (jobs that
    # are pending and miss this argument will behave the same, but
    # it should be called with True only if the carrier_tracking_ref
    # is True when the job is created.
    picking = session.env[model_name].browse(record_id)
    backend_id = picking.backend_id.id
    env = get_environment(session, model_name, backend_id)
    picking_exporter = env.get_connector_unit(MagentoPickingExporter)
    res = picking_exporter.run(record_id)

    if with_tracking and picking.carrier_tracking_ref:
        export_tracking_number.delay(session, model_name, record_id)
    return res
