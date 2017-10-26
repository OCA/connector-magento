# -*- coding: utf-8 -*-
# Copyright 2017 Akretion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import models, fields, api

from odoo.addons.component.core import Component


class MagentoBackend(models.Model):
    _inherit = 'magento.backend'

    import_configurables_from_date = fields.Datetime(
        string='Import configurables from date',
    )

    @api.multi
    def import_product_configurable(self):
        self._import_from_date('magento.product.configurable',
                               'import_configurables_from_date')
        return True

    @api.model
    def _scheduler_import_product_configurable(self, domain=None):
        self._magento_backend('import_product_configurable', domain=domain)


class ProductImporter(Component):
    _inherit = 'magento.product.product.importer'

    """
        Returns None if the product_type is configurable
        So that it is not skipped
    """
    def _must_skip(self):
        res = super(ProductImporter, self)._must_skip()
        if self.magento_record['type_id'] != 'configurable':
            return res


class MagentoProductProduct(models.Model):
    _inherit = 'magento.product.product'

    transformed_at = fields.Date(
        'Transformed At (from simple to templated product)'
    )


class MagentoConfigurableModelBinder(Component):
    _name = 'magento.configurable.binder'
    _inherit = 'magento.binder'
    _apply_on = [
        'magento.product.attribute',
        'magento.product.attribute.value',
        'magento.product.attribute.line',
        'magento.product.attribute.price',
    ]
