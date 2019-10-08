# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create


class ProductAttributeValueDefinitionExporter(Component):
    _name = 'magento.product.attribute.value.exporter'
    _inherit = 'magento.exporter'
    _apply_on = ['magento.product.attribute.value']

    def _should_import(self):
        return False


class MagentoProductAttributeValueExportMapper(Component):
    _name = 'magento.product.attribute.value.export.mapper'
    _inherit = 'magento.export.mapper'
    _apply_on = ['magento.product.attribute.value']

    direct = [
        ('name', 'label'),
    ]

    @mapping
    def code(self, record):
        if record.code:
            return {'value': record.code}

    @mapping
    def is_default(self, record):
        return {'is_default': False}

    @mapping
    def sort_order(self, record):
        return {'sort_order': record.sequence if record.sequence else 0}


class ProductAttributeValueExportMapper(Component):
    _name = 'product.attribute.value.export.mapper'
    _inherit = 'magento.export.mapper'
    _apply_on = ['product.attribute.value']

    direct = [
        ('name', 'label'),
    ]
