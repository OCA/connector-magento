# -*- coding: utf-8 -*-
# Copyright 2019 Callino
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


from odoo.addons.component.core import Component
import logging

_logger = logging.getLogger(__name__)


class ProductTemplateDefinitionExporter(Component):
    _inherit = 'magento.product.template.exporter'

    def _export_product_links(self):
        # TODO: Refactor this to use a real mapping and exporter class
        record = self.binding
        a_products = []
        position = 1
        for p in record.alternative_product_ids:
            binding = p.magento_template_bind_ids.filtered(lambda bc: bc.backend_id.id == record.backend_id.id)
            if not binding or not binding.external_id:
                _logger.info("No binding / No external id on binding for linked product %s", p.display_name)
                continue
            a_products.append({
                "sku": record.external_id,
                "link_type": "related",
                "linked_product_sku": binding.external_id,
                "linked_product_type": "configurable",
                "position": position,
            })
            position += 1
        self.backend_adapter.update_product_links(record.external_id, a_products)

    def _after_export(self):
        self._export_product_links()
        super(ProductTemplateDefinitionExporter, self)._after_export()


class ProductTemplateExportMapper(Component):
    _inherit = 'magento.product.template.export.mapper'

    def category_ids(self, record):
        categ_vals = []
        i = 0
        _logger.info("Public Category IDS: %s", record.public_categ_ids)
        for categ in record.public_categ_ids:
            magento_categ_id = categ.magento_bind_ids.filtered(lambda bc: bc.backend_id.id == record.backend_id.id)
            mpos = self.env['magento.product.position'].search([
                ('product_template_id', '=', record.odoo_id.id),
                ('magento_product_category_id', '=', magento_categ_id.id)
            ])
            if magento_categ_id:
                categ_vals.append({
                  "position": mpos.position if mpos else i,
                  "category_id": magento_categ_id.external_id,
                })
                if not mpos:
                    i += 1
        return {'category_links': categ_vals}
