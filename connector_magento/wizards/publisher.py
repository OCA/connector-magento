from odoo import api, fields, models


class MagentoPublisherWizard(models.TransientModel):
    _name = "wizard.magento.publisher"

    products_to_publish = fields.Many2many("product.product")

    backend_ids = fields.Many2many("magento.backend", required=True)

    @api.model
    def default_get(self, fields):
        res = super(MagentoPublisherWizard, self).default_get(fields)
        product_ids = self.env.context["active_ids"] or []
        active_model = self.env.context["active_model"]

        if not product_ids:
            return res
        assert active_model == "product.product", "Bad context propagation"

        res["products_to_publish"] = [(6, 0, product_ids)]

        return res

    def action_publish_to_magento(self):
        self.products_to_publish.action_publish_to_magento(self.backend_ids)


class MagentoPublisherWizardTemplate(models.TransientModel):
    _name = "wizard.magento.publisher.template"
    # For product.template

    products_to_publish = fields.Many2many("product.template")

    backend_ids = fields.Many2many("magento.backend", required=True)

    @api.model
    def default_get(self, fields):
        res = super(MagentoPublisherWizardTemplate, self).default_get(fields)
        product_ids = self.env.context["active_ids"] or []
        active_model = self.env.context["active_model"]

        if not product_ids:
            return res
        assert active_model == "product.template", "Bad context propagation"

        res["products_to_publish"] = [(6, 0, product_ids)]

        return res

    def action_publish_to_magento(self):
        self.products_to_publish.mapped("product_variant_ids").action_publish_to_magento(self.backend_ids)
