# -*- coding: utf-8 -*-
# Copyright 2017 Akretion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import models, fields
from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class MagentoProductAttribute(models.Model):
    _name = 'magento.product.attribute'
    _inherit = 'magento.binding'
    _inherits = {'product.attribute': 'odoo_id'}
    _description = 'Magento Product Attribute'

    odoo_id = fields.Many2one(
        comodel_name='product.attribute',
        string='Product Attribute',
        required=True,
        ondelete='cascade')


class ProductAttribute(models.Model):
    _inherit = 'product.attribute'

    magento_bind_ids = fields.One2many(
        comodel_name='magento.product.attribute',
        inverse_name='odoo_id',
        string="Magento Bindings",
    )


class ProductAttributeAdapter(Component):
    _name = 'magento.product.attribute.adapter'
    _inherit = 'magento.adapter'
    _apply_on = 'magento.product.attribute'

    _magento_model = 'ol_catalog_product_link'
    _admin_path = '/{model}/index/'

    def list_attributes(self, sku, storeview_id=None, attributes=None):
        """Returns the list of the super attributes and their possible values
        from a specific configurable product

        :rtype: dict
        """
        return self._call('%s.listSuperAttributes' % self._magento_model,
                          [sku, storeview_id, attributes])
