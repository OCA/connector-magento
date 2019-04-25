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
    ]

    @mapping
    def min_qty(self, record):
        return {'min_qty': record.min_qty if record.min_qty else 0.0}

    @mapping
    def backorders(self, record):
        '''
        selection=[('use_default', 'Use Default Config'),
                   ('no', 'No Sell'), = 0
                   ('yes', 'Sell Quantity < 0'), = 1
                   ('yes-and-notification', 'Sell Quantity < 0 and ' = 2
                                            'Use Customer Notification')],
        '''
        if record.backorders == 'use_default':
            return
        map = {
            'no': 0,
            'yes': 1,
            'yes-and-notification': 2
        }
        return {
            'backorders': map[record.backorders],
        }

    @mapping
    def qty(self, record):
        # Get current stock quantity
        stock_field = record.magento_warehouse_id.quantity_field or 'virtual_available'
        if record.magento_warehouse_id.calculation_method == 'real':
            location = record.magento_warehouse_id.lot_stock_id
            product_fields = [stock_field]
            record_with_location = record.with_context(location=location.id)
            result = record_with_location.read(product_fields)[0]
            record.with_context(connector_no_export=True).qty = result[stock_field]
            return {
                'qty': result[stock_field],
                'is_in_stock': True if result[stock_field] > 0 else False,
            }
        elif record.magento_warehouse_id.calculation_method == 'fix':
            record.with_context(connector_no_export=True).qty = record.magento_warehouse_id.fixed_quantity
            return {
                'qty': record.magento_warehouse_id.fixed_quantity,
                'is_in_stock': True if record.magento_warehouse_id.fixed_quantity > 0 else False,
            }
