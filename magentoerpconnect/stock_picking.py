# -*- coding: utf-8 -*-
# © 2013 Guewen Baconnier,Camptocamp SA,Akretion
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import xmlrpclib
import odoo
from odoo import _, api, models, fields
from odoo.addons.queue_job.job import job, related_action
from odoo.addons.queue_job.exception import NothingToDoJob
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

    def add_tracking_number(self, external_id, carrier_code,
                            tracking_title, tracking_number):
        """ Add new tracking number.

        :param external_id: shipment increment id
        :param carrier_code: code of the carrier on Magento
        :param tracking_title: title displayed on Magento for the tracking
        :param tracking_number: tracking number
        """
        return self._call('%s.addTrack' % self._magento_model,
                          [external_id, carrier_code,
                           tracking_title, tracking_number])

    def get_carriers(self, external_id):
        """ Get the list of carrier codes allowed for the shipping.

        :param external_id: order increment id
        :rtype: list
        """
        return self._call('%s.getCarriers' % self._magento_model,
                          [external_id])


class MagentoPickingExporter(Component):
    _name = 'magento.stock.picking.exporter'
    _inherit = 'magento.exporter'
    _apply_on = ['magento.stock.picking']

    def _get_args(self, binding, lines_info=None):
        if lines_info is None:
            lines_info = {}
        sale_binder = self.binder_for('magento.sale.order')
        magento_sale_id = sale_binder.to_external(binding.magento_order_id)
        mail_notification = self._get_picking_mail_option(binding)
        return (magento_sale_id, lines_info,
                _("Shipping Created"), mail_notification, True)

    def _get_lines_info(self, binding):
        """
        Get the line to export to Magento. In case some lines doesn't have a
        matching on Magento, we ignore them. This allow to add lines manually.

        :param binding: magento.stock.picking record
        :return: dict of {magento_product_id: quantity}
        :rtype: dict
        """
        item_qty = {}
        # get product and quantities to ship from the picking
        for line in binding.move_lines:
            sale_line = line.procurement_id.sale_line_id
            if not sale_line.magento_bind_ids:
                continue
            magento_sale_line = next(
                (line for line in sale_line.magento_bind_ids
                 if line.backend_id.id == binding.backend_id.id),
                None
            )
            if not magento_sale_line:
                continue
            item_id = magento_sale_line.external_id
            item_qty.setdefault(item_id, 0)
            item_qty[item_id] += line.product_qty
        return item_qty

    def _get_picking_mail_option(self, binding):
        """ Indicates if Magento has to send an email

        :param binding: magento.stock.picking record
        :returns: value of send_picking_done_mail chosen on magento shop
        :rtype: boolean
        """
        magento_shop = binding.sale_id.magento_bind_ids[0].store_id
        return magento_shop.send_picking_done_mail

    def run(self, binding):
        """
        Export the picking to Magento
        """
        if binding.external_id:
            return _('Already exported')
        picking_method = binding.picking_method
        if picking_method == 'complete':
            args = self._get_args(binding)
        elif picking_method == 'partial':
            lines_info = self._get_lines_info(binding)
            if not lines_info:
                raise NothingToDoJob(_('Canceled: the delivery order does not '
                                       'contain lines from the original '
                                       'sale order.'))
            args = self._get_args(binding, lines_info)
        else:
            raise ValueError("Wrong value for picking_method, authorized "
                             "values are 'partial' or 'complete', "
                             "found: %s" % picking_method)
        try:
            external_id = self.backend_adapter.create(*args)
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
            self.binder.bind(external_id, binding)
            # ensure that we store the external ID
            if not odoo.tools.config['test_enable']:
                self.env.cr.commit()


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
            binding.with_delay(priority=20).export_tracking()

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
