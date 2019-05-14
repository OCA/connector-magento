# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# Copyright 2019 Callino
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import Component
from odoo.addons.connector.unit.mapper import mapping, only_create


class MagentoStockItemExporter(Component):
    _name = 'magento.stock.item.exporter'
    _inherit = 'magento.exporter'
    _apply_on = ['magento.stock.item']

    def _should_import(self):
        return False

    def _after_export(self):
        self.binding.with_context(connector_no_export=True).qty = self.binding.calculated_qty


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
        return {
            'qty': record.calculated_qty,
            'is_in_stock': True if record.product_type=='configurable' or record.calculated_qty > 0 else False,
        }
