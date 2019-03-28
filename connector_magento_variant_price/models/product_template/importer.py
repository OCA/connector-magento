# -*- coding: utf-8 -*-
# © 2019 Wolfgang Pichler,Callino
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo.addons.component.core import Component


class ProductTemplateImporter(Component):
    _inherit = 'magento.product.template.importer'

    def _update_price(self, binding, price):
        # Update price if price is 0
        if binding.price == 0:
            # We have to call the price update with skip fix price - else our variant prices would get overwritten
            binding.with_context(skip_update_fix_price=True).price = price
