# -*- coding: utf-8 -*-
# Copyright 2019 Callino
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


from odoo.addons.component.core import Component
import logging

_logger = logging.getLogger(__name__)


class ProductTemplateDefinitionExporter(Component):
    _inherit = 'magento.product.template.exporter'


class ProductTemplateExportMapper(Component):
    _inherit = 'magento.product.template.export.mapper'

    def category_ids(self, record):
        position = 0
        categ_vals = []
        _logger.info("Public Category IDS: %s", record.public_categ_ids)
        for categ in record.public_categ_ids:
            magento_categ_id = categ.magento_bind_ids.filtered(lambda bc: bc.backend_id.id == record.backend_id.id)
            categ_vals.append({
              "position": position,
              "category_id": magento_categ_id.external_id,
            })
            position += 1
        return {'category_links': categ_vals}
