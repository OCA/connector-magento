# -*- coding: utf-8 -*-
# Copyright 2017 Akretion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import xmlrpclib
from odoo import models, fields
from odoo.addons.connector.exception import IDMissingInBackend
from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class MagentoProductAttributeLine(models.Model):
    _name = 'magento.product.attribute.line'
    _inherit = 'magento.binding'
    _inherits = {'product.attribute.line': 'odoo_id'}
    _description = 'Magento Product Attribute Line'

    odoo_id = fields.Many2one(
        comodel_name='product.attribute.line',
        string='Product Attribute Line',
        required=True,
        ondelete='cascade')


class ProductAttributeLine(models.Model):
    _inherit = 'product.attribute.line'

    magento_bind_ids = fields.One2many(
        comodel_name='magento.product.attribute.line',
        inverse_name='odoo_id',
        string="Magento Bindings",
    )


class ProductAttributeLineAdapter(Component):
    _name = 'magento.product.attribute.line.adapter'
    _inherit = 'magento.adapter'
    _apply_on = 'magento.product.attribute.line'

    _magento_model = 'ol_catalog_product_link'
    _admin_path = '/{model}/index/'

    def _call(self, method, arguments):
        try:
            return super(ProductAttributeLineAdapter, self)._call(
                method,
                arguments)
        except xmlrpclib.Fault as err:
            # 101 is the error in the Magento API
            # when the attribute does not exist
            if err.faultCode == 101:
                raise IDMissingInBackend
            else:
                raise

    def list_variants(self, sku, storeview_id=None, attributes=None):
        """ Returns the information of a record

        :rtype: dict
        """
        return self._call('%s.list' % self._magento_model,
                          [sku, storeview_id, attributes])
