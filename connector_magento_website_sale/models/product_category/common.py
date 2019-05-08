# -*- coding: utf-8 -*-
# © 2019 Callino
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


import logging
from odoo import models, fields

_logger = logging.getLogger(__name__)


class MagentoProductCategory(models.Model):
    _inherit = 'magento.product.category'

    # Use product.public.category if website_sale is installed
    public_categ_id = fields.Many2one(comodel_name='product.public.category',
                                      string='Public Product Category',
                                      required=False,
                                      ondelete='cascade')


class ProductCategory(models.Model):
    _inherit = 'product.public.category'

    magento_bind_ids = fields.One2many(
        comodel_name='magento.product.category',
        inverse_name='public_categ_id',
        string="Magento Bindings",
    )
