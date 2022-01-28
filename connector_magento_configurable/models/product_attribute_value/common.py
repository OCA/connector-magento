# -*- coding: utf-8 -*-
# Copyright 2017 Akretion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from odoo import models, fields

_logger = logging.getLogger(__name__)


class MagentoProductAttributeValue(models.Model):
    _name = 'magento.product.attribute.value'
    _inherit = 'magento.binding'
    _inherits = {'product.attribute.value': 'odoo_id'}
    _description = 'Magento Product Attribute'

    odoo_id = fields.Many2one(
        comodel_name='product.attribute.value',
        string='Product Attribute',
        required=True,
        ondelete='cascade')

    magento_attribute_id = fields.Many2one(
        comodel_name='magento.product.attribute',
        string='Magento Attribute',
        ondelete='cascade',
    )


class ProductAttributeValue(models.Model):
    _inherit = 'product.attribute.value'

    magento_bind_ids = fields.One2many(
        comodel_name='magento.product.attribute.value',
        inverse_name='odoo_id',
        string="Magento Bindings",
    )
