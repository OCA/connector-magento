# -*- coding: utf-8 -*-
# Copyright 2017 Akretion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields
from odoo.addons.component.core import Component


class MagentoProductTemplate(models.Model):
    _name = 'magento.product.template'
    _inherit = 'magento.binding'
    _inherits = {'product.template': 'odoo_id'}
    _description = 'Magento Product Template'

    odoo_id = fields.Many2one(
        comodel_name='product.template',
        string='Product Template',
        required=True,
        ondelete='cascade')


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    magento_bind_ids = fields.One2many(
        comodel_name='magento.product.template',
        inverse_name='odoo_id',
        string='Magento Bindings',
    )

    variant_managed_by_magento = fields.Boolean(
    )

    def create_variant_ids(self):
        for record in self:
            if not record.variant_managed_by_magento:
                super(ProductTemplate, record).create_variant_ids()
        return True


class ProductTemplateAdapter(Component):
    _name = 'magento.product.template.adapter'
    _inherit = 'magento.product.product.adapter'
    _apply_on = 'magento.product.template'
    _tmpl_magento_model = 'ol_catalog_product_link'
    _tmpl_admin_path = '/{model}/index/'

    def search(self, filters=None, from_date=None, to_date=None):
        if filters is None:
            filters = {}
        filters['type'] = 'configurable'

        return super(ProductTemplateAdapter, self).search(
            filters, from_date, to_date)

    def list_attributes(self, sku, storeview_id=None, attributes=None):
        """Returns the list of the super attributes and their possible values
        from a specific configurable product

        :rtype: dict
        """
        return self._call('%s.listSuperAttributes' % self._tmpl_magento_model,
                          [sku, storeview_id, attributes])

    def list_variants(self, sku, storeview_id=None, attributes=None):
        """ Returns the information of a record

        :rtype: dict
        """
        return self._call('%s.list' % self._tmpl_magento_model,
                          [sku, storeview_id, attributes])
