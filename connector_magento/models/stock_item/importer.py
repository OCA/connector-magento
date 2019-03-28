# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import _
from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create
from odoo.addons.connector.exception import MappingError
import json


class MagentoStockItemImportMapper(Component):
    _name = 'magento.stock.item.import.mapper'
    _inherit = 'magento.import.mapper'
    _apply_on = 'magento.stock.item'

    direct = [
        ('qty', 'qty'),
        ('min_sale_qty', 'min_sale_qty'),
        ('is_qty_decimal', 'is_qty_decimal'),
        ('is_in_stock', 'is_in_stock'),
        ('min_qty', 'min_qty'),
        ('item_id', 'external_id'),
    ]
    
    @mapping
    @only_create
    def odoo_id(self, record):
        binder = self.binder_for('magento.product.product')
        mproduct = binder.to_internal(record['product_id'], external_field='magento_id', unwrap=False)
        return {
            'odoo_id': mproduct.odoo_id.id,
            'magento_product_binding_id': mproduct.id
        }

    @mapping
    @only_create
    def warehouse_id(self, record):
        binder = self.binder_for('magento.stock.warehouse')
        mwarehouse = binder.to_internal(record['stock_id'], unwrap=False)
        return {
            'magento_warehouse_id': mwarehouse.id,
        }

    @mapping
    def backorders(self, record):
        # TODO: Find out how to control this
        return {'backorders': 'use_default'}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}


class MagentoStockItemImporter(Component):
    _name = 'magento.stock.item.importer'
    _inherit = 'magento.importer'
    _apply_on = 'magento.stock.item'
    _magento_id_field = 'item_id'
