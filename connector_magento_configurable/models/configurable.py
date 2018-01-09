# -*- coding: utf-8 -*-
# Copyright 2017 Akretion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging

from odoo import models, fields

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class ConfigurableBatchImporter(Component):
    """ Import the Configurable Products.

    For every Configurable Product not yet converted from flat
    to templated product, creates a job
    """
    _name = 'magento.product.configurable.batch.importer'
    _inherit = 'magento.delayed.batch.importer'
    _apply_on = ['magento.product.configurable']

    def search_active_only(self):
        """ Allows to be easily overriden"""
        return True

    def run(self, filters=None):
        """ Run the synchronization """
        from_date = filters.pop('from_date', None)
        criterias = [('product_type', '=', 'configurable')]
        if from_date:
            criterias.append(('write_date', '>', fields.DateTime.to_string()))
        configurables = self.env['magento.product.product'].with_context(
            active_test=self.search_active_only()
            ).search(criterias)
        _logger.info('search for configurable products %s returned %s',
                     filters, configurables)
        for configurable in configurables:
            self._import_record(configurable)


class ConfigurableImporter(Component):
    _name = 'magento.product.configurable.importer'
    _inherit = 'magento.importer'
    _apply_on = ['magento.product.configurable']

    def run(self, record, force=False):
        filters = {'record': record}
        self.env['magento.product.attribute'].import_batch(
            self.backend_record,
            filters,
        )
        self.env['magento.product.attribute.line'].import_batch(
            self.backend_record,
            filters,
        )


class MagentoProductConfigurable(models.Model):
    _name = 'magento.product.configurable'
    _inherit = 'magento.binding'
    _inherits = {'product.product': 'odoo_id'}
    _description = 'Magento Product Configurable'

    odoo_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
        required=True,
        ondelete='cascade')
