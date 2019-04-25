# -*- coding: utf-8 -*-
# Copyright <YEAR(S)> <AUTHOR(S)>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models, fields, _


class WizardModel(models.TransientModel):
    _inherit = "connector_magento.add_backend.wizard"

    @api.multi
    def get_default_products(self):
        return self.get_default_object('product.product')

    @api.multi
    def get_default_product_templates(self):
        return self.get_default_object('product.template')

    @api.multi
    def get_default_category(self):
        return self.get_default_object('product.category')

    @api.multi
    def _get_ids_and_model(self):
        active_model = self.env.context.get('active_model', False)
        if active_model == 'product.template':
            return (self.temp_export_ids, 'magento.product.template')
        elif active_model == 'product.product':
            return (self.to_export_ids, 'magento.product.product')
        elif active_model == 'product.category':
            return (self.categ_to_export_ids, 'magento.product.category')
        else:
            return super(WizardModel, self)._get_ids_and_model()

    @api.multi
    def check_backend_binding(self, to_export_ids=None, dest_model=None):
        if not dest_model or not to_export_ids:
            (to_export_ids, dest_model) = self._get_ids_and_model()
        if dest_model == 'magento.product.template' and self.product_type == 'simple':
            # We have to change it to magento.product.product
            dest_model = "magento.product.product"
            # And use the product ids instead
            variant_ids = self.env['product.product']
            for template in to_export_ids:
                if template.product_variant_count > 1:
                    raise UserWarning(_(u'Product template with variants can not get exported as simple product !'))
                variant_ids += template.product_variant_id
            to_export_ids = variant_ids
        return super(WizardModel, self).check_backend_binding(to_export_ids, dest_model)

    model = fields.Selection(selection_add=[
        ('product.template', _(u'Product templates')),
        ('product.product', _(u'Product')),
        ('product.category', _(u'Product category')),
    ], string='Model')
    product_type = fields.Selection(selection=[
        ('simple', _(u'Simple')),
        ('configurable', _(u'Configurable')),
    ], default='simple', string="Product Type")
    to_export_ids = fields.Many2many(string='Products to export',
                                     comodel_name='product.product', default=get_default_products)
    temp_export_ids = fields.Many2many(string='Product Templates to export',
                                       comodel_name='product.template', default=get_default_product_templates)

    categ_to_export_ids = fields.Many2many(string='Category To export',
                                           comodel_name='product.category', default=get_default_category)
