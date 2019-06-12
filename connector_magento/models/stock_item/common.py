# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from odoo import api, models, fields
from odoo.addons.queue_job.job import job, related_action
from odoo.addons.component.core import Component
from odoo.addons.queue_job.job import identity_exact

_logger = logging.getLogger(__name__)


class MagentoStockItem(models.Model):
    _name = 'magento.stock.item'
    _inherit = 'magento.binding'
    _description = 'Magento Stock Item'

    @api.depends('magento_warehouse_id', 'qty', 'magento_product_binding_id', 'magento_product_binding_id.no_stock_sync')
    def _compute_qty(self):
        for stockitem in self:
            stock_field = stockitem.magento_warehouse_id.quantity_field or 'virtual_available'
            if stockitem.magento_warehouse_id.calculation_method == 'real':
                location = stockitem.magento_warehouse_id.lot_stock_id
                product_fields = [stock_field]
                if stockitem.product_type=='product':
                    record_with_location = stockitem.magento_product_binding_id.odoo_id.with_context(
                        location=location.id)
                else:
                    record_with_location = stockitem.magento_product_template_binding_id.odoo_id.with_context(
                        location=location.id)
                result = record_with_location.read(product_fields)[0]
                stockitem.calculated_qty = result[stock_field]
            elif stockitem.magento_warehouse_id.calculation_method == 'fix':
                stockitem.calculated_qty = stockitem.magento_warehouse_id.fixed_quantity

            if stockitem.magento_product_binding_id.no_stock_sync:
                # Never export if no stock sync is enabled
                stockitem.should_export = False
                continue
            if stockitem.calculated_qty == stockitem.qty:
                # Do not export when last exported qty is the same as the current
                stockitem.should_export = False
                continue
            stockitem.should_export = True


    magento_product_binding_id = fields.Many2one(comodel_name='magento.product.product',
                                                 string='Product',
                                                 required=False,
                                                 ondelete='cascade')
    magento_product_template_binding_id = fields.Many2one(comodel_name='magento.product.template',
                                                          string='Product Template',
                                                          required=False,
                                                          ondelete='cascade')
    product_type = fields.Selection([
        ('product', 'Product'),
        ('configurable', 'Configurable'),
    ], default='product', string="Product Type")
    magento_warehouse_id = fields.Many2one(comodel_name='magento.stock.warehouse',
                                           string='Warehouse',
                                           required=True,
                                           ondelete='cascade')
    qty = fields.Float(string='Quantity', default=-999)
    calculated_qty = fields.Float(string='Calculated Qty.', compute='_compute_qty')
    should_export = fields.Boolean(string='Should Export', compute='_compute_qty')
    min_sale_qty = fields.Float(string='Min Sale Qty', default=1.0)
    is_qty_decimal = fields.Boolean(string='Decimal Qty.', default=False)
    is_in_stock = fields.Boolean(string='In Stock From Magento')
    min_qty = fields.Float('Min. Qty.', default=0.0)
    backorders = fields.Selection(
        selection=[('use_default', 'Use Default Config'),
                   ('no', 'No Sell'),
                   ('yes', 'Sell Quantity < 0'),
                   ('yes-and-notification', 'Sell Quantity < 0 and '
                                            'Use Customer Notification')],
        string='Manage Inventory Backorders',
        default='use_default',
        required=True,
    )

    @api.multi
    @job(default_channel='root.magento.stock')
    def sync_from_magento(self):
        for binding in self:
            binding.with_delay(priority=5, identity_key=identity_exact).run_sync_from_magento()

    @api.multi
    @job(default_channel='root.magento.stock')
    def run_sync_from_magento(self):
        self.ensure_one()
        with self.backend_id.work_on(self._name) as work:
            importer = work.component(usage='record.importer')
            return importer.run(self.external_id, force=True, binding=self)

    @api.multi
    @job(default_channel='root.magento.stock')
    def sync_to_magento(self):
        for binding in self:
            if binding.should_export:
                binding.with_delay(priority=5, identity_key=identity_exact).run_sync_to_magento()

    @api.multi
    @job(default_channel='root.magento.stock')
    def run_sync_to_magento(self):
        self.ensure_one()
        with self.backend_id.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            return exporter.run(self)


class MagentoStockItemAdapter(Component):
    _name = 'magento.stock.item.adapter'
    _inherit = 'magento.adapter'
    _apply_on = 'magento.stock.item'

    _magento_model = 'stockItems'
    _magento2_model = 'stockItems/%(sku)s'
    _magento2_name = 'stockItem'
    _magento2_search = 'stock/search'
    _magento2_key = 'id'
    _admin_path = '/{model}/edit/id/{id}'

    def _write_url(self, id, binding):
        if binding.product_type=='product':
            return "products/%(sku)s/stockItems/%(id)s" % {
                'sku': binding.magento_product_binding_id.external_id,
                'id': binding.external_id
            }
        else:
            return "products/%(sku)s/stockItems/%(id)s" % {
                'sku': binding.magento_product_template_binding_id.external_id,
                'id': binding.external_id
            }

    def _read_url(self, id, binding):
        if binding.product_type=='product':
            return 'stockItems/%(sku)s' % {
                'sku': binding.magento_product_binding_id.external_id,
            }
        else:
            return 'stockItems/%(sku)s' % {
                'sku': binding.magento_product_template_binding_id.external_id,
            }
