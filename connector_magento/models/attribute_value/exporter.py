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


class ProductAttributeValueDefinitionExporter(Component):
    _name = 'magento.product.attribute.value.exporter'
    _inherit = 'magento.exporter'
    _apply_on = ['magento.product.attribute.value']

    def _should_import(self):
        return False

class ProductAttributeValueExportMapper(Component):
    _name = 'magento.product.attribute.value.export.mapper'
    _inherit = 'magento.export.mapper'
    _apply_on = ['magento.product.attribute.value']
    _magento_name = 'attribute'

    direct = [
        ('name', 'name')
    ]
