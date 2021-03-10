from odoo import _, api, fields, models
from odoo.exceptions import UserError


class MagentoContentSyncWizard(models.TransientModel):
    _name = "wizard.content.magento.sync"

    products_to_sync = fields.Many2many("product.product")

    def action_sync_content_to_magento(self):
        no_bind_ids = self.with_context(active_test=False).products_to_sync.filtered(
            lambda p: not p.magento_bind_ids
        )
        if no_bind_ids:
            raise UserError(_("Products are missing Magento Bindings"))

        for record in self.products_to_sync:
            if not record.with_context(active_test=False).magento_bind_ids:
                continue

            for binding in record.with_context(active_test=False).magento_bind_ids:
                binding.with_delay().export_inventory([])

    @api.model
    def default_get(self, fields):
        res = super(MagentoContentSyncWizard, self).default_get(fields)
        product_ids = self.env.context["active_ids"] or []
        active_model = self.env.context["active_model"]

        if not product_ids:
            return res
        assert active_model == "product.product", "Bad context propagation"

        res["products_to_sync"] = [(6, 0, product_ids)]

        return res
