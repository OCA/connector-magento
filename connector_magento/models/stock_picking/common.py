# Copyright 2013-2019 Camptocamp SA
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import xmlrpc.client
from odoo import api, models, fields
from odoo.addons.queue_job.job import job, related_action
from odoo.addons.connector.exception import IDMissingInBackend
from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class MagentoStockPicking(models.Model):
    _name = 'magento.stock.picking'
    _inherit = 'magento.binding'
    _inherits = {'stock.picking': 'odoo_id'}
    _description = 'Magento Delivery Order'

    odoo_id = fields.Many2one(comodel_name='stock.picking',
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

    @job(default_channel='root.magento')
    @related_action(action='related_action_unwrap_binding')
    @api.multi
    def export_tracking_number(self):
        """ Export the tracking number of a delivery order. """
        self.ensure_one()
        with self.backend_id.work_on(self._name) as work:
            exporter = work.component(usage='tracking.exporter')
            return exporter.run(self)

    @job(default_channel='root.magento')
    @related_action(action='related_action_unwrap_binding')
    @api.multi
    def export_picking_done(self, with_tracking=True):
        """ Export a complete or partial delivery order. """
        # with_tracking is True to keep a backward compatibility (jobs that
        # are pending and miss this argument will behave the same, but
        # it should be called with True only if the carrier_tracking_ref
        # is True when the job is created.
        self.ensure_one()
        with self.backend_id.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            res = exporter.run(self)
            if with_tracking and self.carrier_tracking_ref:
                self.with_delay().export_tracking_number()
            return res


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    magento_bind_ids = fields.One2many(
        comodel_name='magento.stock.picking',
        inverse_name='odoo_id',
        string="Magento Bindings",
    )


class StockPickingAdapter(Component):
    _name = 'magento.stock.picking.adapter'
    _inherit = 'magento.adapter'
    _apply_on = 'magento.stock.picking'

    _magento_model = 'sales_order_shipment'
    _admin_path = 'sales_shipment/view/shipment_id/{id}'

    def _call(self, method, arguments, http_method=None, storeview=None):
        try:
            return super(StockPickingAdapter, self)._call(
                method, arguments, http_method=http_method,
                storeview=storeview)
        except xmlrpc.client.Fault as err:
            # this is the error in the Magento API
            # when the shipment does not exist
            if err.faultCode == 100:
                raise IDMissingInBackend
            else:
                raise

    def create(self, order_id, items, comment, email, include_comment):
        """ Create a record on the external system """
        # pylint: disable=method-required-super
        return self._call('%s.create' % self._magento_model,
                          [order_id, items, comment, email, include_comment])

    def add_tracking_number(self, *arguments):
        """ Add new tracking number.

        In the case of Magento 1.x, arguments is a list consisting of
        * external_id: shipment increment id
        * carrier_code: code of the carrier on Magento
        * tracking_title: title displayed on Magento for the tracking
        * tracking_number: tracking number

        In the case of Magento 2.x its only member is a json dict
        """
        if self.collection.version == '2.0':
            _external_id, json_data = arguments
            return self._call(
                'shipment/track', json_data, http_method='post')
        return self._call('%s.addTrack' % self._magento_model,
                          arguments)

    def get_carriers(self, external_id):
        """ Get the list of carrier codes allowed for the shipping.

        :param external_id: order increment id
        :rtype: list
        """
        return self._call('%s.getCarriers' % self._magento_model,
                          [external_id])


class MagentoBindingStockPickingListener(Component):
    _name = 'magento.binding.stock.picking.listener'
    _inherit = 'base.event.listener'
    _apply_on = ['magento.stock.picking']

    def on_record_create(self, record, fields=None):
        # tracking number is sent when:
        # * the picking is exported and the tracking number was already
        #   there before the picking was done OR
        # * the tracking number is added after the picking is done
        # We have to keep the initial state of whether we had an
        # tracking number in the job kwargs, because if we read the
        # picking at the time of execution of the job, a tracking could
        # have been added and it would be exported twice.
        with_tracking = bool(record.carrier_tracking_ref)
        record.with_delay().export_picking_done(with_tracking=with_tracking)


class MagentoStockPickingListener(Component):
    _name = 'magento.stock.picking.listener'
    _inherit = 'base.event.listener'
    _apply_on = ['stock.picking']

    def on_tracking_number_added(self, record):
        for binding in record.magento_bind_ids:
            # Set the priority to 20 to have more chance that it would be
            # executed after the picking creation
            binding.with_delay(priority=20).export_tracking_number()

    def on_picking_dropship_done(self, record, picking_method):
        return self.on_picking_out_done(record, picking_method)

    def on_picking_out_done(self, record, picking_method):
        """
        Create a ``magento.stock.picking`` record. This record will then
        be exported to Magento.

        :param picking_method: picking_method, can be 'complete' or 'partial'
        :type picking_method: str
        """
        sale = record.sale_id
        if not sale:
            return
        for magento_sale in sale.magento_bind_ids:
            self.env['magento.stock.picking'].create({
                'backend_id': magento_sale.backend_id.id,
                'odoo_id': record.id,
                'magento_order_id': magento_sale.id,
                'picking_method': picking_method})
