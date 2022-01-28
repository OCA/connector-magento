# -*- coding: utf-8 -*-
# Copyright 2017 Akretion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from odoo import models, fields

_logger = logging.getLogger(__name__)


class MagentoProductAttributePrice(models.Model):
    _name = 'magento.product.attribute.price'
    _inherit = 'magento.binding'
    _inherits = {'product.attribute.price': 'odoo_id'}
    _description = 'Magento Product Attribute'

    odoo_id = fields.Many2one(
        comodel_name='product.attribute.price',
        string='Product Attribute',
        required=True,
        ondelete='cascade')


class ProductAttributePrice(models.Model):
    _inherit = 'product.attribute.price'

    magento_bind_ids = fields.One2many(
        comodel_name='magento.product.attribute.price',
        inverse_name='odoo_id',
        string="Magento Bindings",
    )
