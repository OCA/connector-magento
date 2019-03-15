# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import xmlrpclib

import odoo
from datetime import datetime

from odoo import _
from odoo.addons.component.core import Component
from odoo.addons.queue_job.exception import NothingToDoJob
from odoo.addons.connector.unit.mapper import mapping
from odoo.addons.queue_job.job import identity_exact

from odoo.addons.connector_magento.components.backend_adapter import MAGENTO_DATETIME_FORMAT


class ProductAttributeDefinitionExporter(Component):
    _name = 'magento.product.attribute.exporter'
    _inherit = 'magento.exporter'
    _apply_on = ['magento.product.attribute']

    def _should_import(self):
        return False

    def _after_export(self):
        # Here we do check for not exported attribute values - and we do export them
        exported_ids = [mvalue.odoo_id.id for mvalue in self.binding.magento_attribute_value_ids]
        export_values = self.binding.value_ids.filtered(lambda v: v.id not in exported_ids)
        for value in export_values:
            self._export_dependency(value, 'magento.product.attribute.value', binding_extra_vals={
                'magento_attribute_id': self.binding.id
            })


class ProductAttributeExportMapper(Component):
    _name = 'magento.product.attribute.export.mapper'
    _inherit = 'magento.export.mapper'
    _apply_on = ['magento.product.attribute']

    children = [
        ('magento_attribute_value_ids', 'options', 'magento.product.attribute.value'),
    ]

    '''
    No Support for translatable currently on export !
    translatable = [
        ('name', 'default_frontend_label')
    ]
    '''

    direct = [
        ('attribute_code', 'attribute_code'),
        ('attribute_id', 'attribute_id'),
        ('name', 'default_frontend_label')
    ]
