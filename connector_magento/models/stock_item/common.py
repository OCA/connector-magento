# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import xmlrpclib
from odoo import api, models, fields
from odoo.addons.queue_job.job import job, related_action
from odoo.addons.connector.exception import IDMissingInBackend
from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)

'''
            "item_id": 1237,
            "product_id": 1198,
            "stock_id": 1,
            "qty": 0,
            "is_in_stock": true,
            "is_qty_decimal": false,
            "show_default_notification_message": false,
            "use_config_min_qty": true,
            "min_qty": 0,
            "use_config_min_sale_qty": 1,
            "min_sale_qty": 1,
            "use_config_max_sale_qty": true,
            "max_sale_qty": 10000,
            "use_config_backorders": true,
            "backorders": 0,
            "use_config_notify_stock_qty": true,
            "notify_stock_qty": 1,
            "use_config_qty_increments": true,
            "qty_increments": 0,
            "use_config_enable_qty_inc": true,
            "enable_qty_increments": false,
            "use_config_manage_stock": true,
            "manage_stock": true,
            "low_stock_date": null,
            "is_decimal_divided": false,
            "stock_status_changed_auto": 0
'''

class MagentoStockItem(models.Model):
    _name = 'magento.stock.item'
    _inherit = 'magento.binding'
    _description = 'Magento Stock Item'
    _inherits = {'product.product': 'odoo_id'}

    odoo_id = fields.Many2one(comodel_name='product.product',
                              string='Product',
                              required=True,
                              ondelete='cascade')
    magento_product_binding_id = fields.Many2one(comodel_name='magento.product.product',
                                                 string='Product',
                                                 required=True,
                                                 ondelete='cascade')
    magento_warehouse_id = fields.Many2one(comodel_name='magento.stock.warehouse',
                                           string='Warehouse',
                                           required=True,
                                           ondelete='cascade')
    qty = fields.Float(string='Quantity', default=0.0)
    min_sale_qty = fields.Float(string='Min Sale Qty', default=1.0)
    is_qty_decimal = fields.Boolean(string='Decimal Qty.', default=False)
    is_in_stock = fields.Boolean(string='In Stock')
    min_qty = fields.Float('Min. Qty.', default=0.0)



class ProductProduct(models.Model):
    _inherit = 'product.product'

    magento_stock_item_ids = fields.One2many(
        comodel_name='magento.stock.item',
        inverse_name='odoo_id',
        string="Magento Stock Items",
    )


class MagentoStockItemAdapter(Component):
    _name = 'magento.stock.item.adapter'
    _inherit = 'magento.adapter'
    _apply_on = 'magento.stock.item'

    _magento_model = 'stockItems'
    _magento2_model = 'products/%(sku)s/stockItems/%(id)s'
    _magento2_name = 'stockItem'
    _magento2_search = 'stock/search'
    _magento2_key = 'id'
    _admin_path = '/{model}/edit/id/{id}'

    def _write_url(self, id, binding):
        return self._magento2_model % {
            'sku': binding.magento_product_binding_id.external_id,
            'id': binding.external_id
        }