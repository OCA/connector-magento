# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import xmlrpclib
from odoo import api, models, fields
from odoo.addons.queue_job.job import job, related_action
from odoo.addons.connector.exception import IDMissingInBackend
from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class MagentoStockWarehouse(models.Model):
    _name = 'magento.stock.warehouse'
    _inherit = 'magento.binding'
    _inherits = {'stock.warehouse': 'odoo_id'}
    _description = 'Magento Warehouse'

    odoo_id = fields.Many2one(comodel_name='stock.warehouse',
                              string='Warehouse',
                              required=True,
                              ondelete='cascade')
    location_id = fields.Many2one(comodel_name='stock.location',
                                  string='Location',
                                  ondelete='cascade')
    quantity_field = fields.Selection([
        ('qty_available', 'Available Quantity'),
        ('virtual_available', 'Forecast quantity')
    ], string='Field use for quantity update', required=True, default='virtual_available')
    calculation_method = fields.Selection([
        ('real', 'Use Quantity Field'),
        ('fix', 'Use Fixed Quantity'),
    ], default='real', string='Calculation Method')
    fixed_quantity = fields.Float('Fixed Quantity', default=0.0)
    magento_stock_item_ids = fields.One2many(
        comodel_name='magento.stock.item',
        inverse_name='magento_warehouse_id',
        string="Magento Stock Items",
    )

    @job(default_channel='root.magento')
    @related_action(action='related_action_unwrap_binding')
    @api.multi
    def export_stock(self):
        """ Export the the current stock items """
        self.ensure_one()
        with self.backend_id.work_on(self._name) as work:
            # TODO:
            exporter = work.component(usage='record.exporter')
            return exporter.run(self)

    @job(default_channel='root.magento')
    @related_action(action='related_action_unwrap_binding')
    @api.multi
    def import_stock(self):
        """ Export a complete or partial delivery order. """
        # with_tracking is True to keep a backward compatibility (jobs that
        # are pending and miss this argument will behave the same, but
        # it should be called with True only if the carrier_tracking_ref
        # is True when the job is created.
        self.ensure_one()
        with self.backend_id.work_on(self._name) as work:
            # TODO
            pass


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    magento_bind_ids = fields.One2many(
        comodel_name='magento.stock.warehouse',
        inverse_name='odoo_id',
        string="Magento Bindings",
    )
