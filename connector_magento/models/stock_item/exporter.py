# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import Component
from odoo.addons.connector.unit.mapper import mapping, only_create


class MagentoStockItemExporter(Component):
    _name = 'magento.stock.item.exporter'
    _inherit = 'magento.exporter'
    _apply_on = ['magento.stock.item']

    def _should_import(self):
        return False


class MagentoStockItemExportMapper(Component):
    _name = 'magento.stock.item.export.mapper'
    _inherit = 'magento.export.mapper'
    _apply_on = ['magento.stock.item']

    direct = [
        ('min_sale_qty', 'min_sale_qty'),
        ('is_qty_decimal', 'is_qty_decimal'),
        ('is_in_stock', 'is_in_stock'),
        ('backorders', 'backorders'),
    ]

    @mapping
    def min_qty(self, record):
        return {'min_qty': record.min_qty if record.min_qty else 0.0}

    @mapping
    def qty(self, record):
        # Get current stock quantity
        stock_field = record.magento_warehouse_id.quantity_field or 'virtual_available'
        if record.magento_warehouse_id.calculation_method == 'real':
            location = record.magento_warehouse_id.lot_stock_id
            product_fields = [stock_field]
            record_with_location = record.with_context(location=location.id)
            result = record_with_location.read(product_fields)[0]
            return {
                'qty': result[stock_field]
            }
        elif record.magento_warehouse_id.calculation_method == 'fix':
            return {
                'qty': record.magento_warehouse_id.fixed_quantity
            }
