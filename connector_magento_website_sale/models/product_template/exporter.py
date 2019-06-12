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
            if not binding:
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


'''
    alternative_product_ids = fields.Many2many('product.template', 'product_alternative_rel', 'src_id', 'dest_id',
                                               string='Alternative Products', help='Suggest more expensive alternatives to '
                                               'your customers (upsell strategy). Those products show up on the product page.')
    accessory_product_ids = fields.Many2many('product.product', 'product_accessory_rel', 'src_id', 'dest_id',
                                             string='Accessory Products', help='Accessories show up when the customer reviews the '
                                             'cart before paying (cross-sell strategy, e.g. for computers: mouse, keyboard, etc.). '
                                             'An algorithm figures out a list of accessories based on all the products added to cart.')
'''