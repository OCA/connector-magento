# -*- coding: utf-8 -*-
# Copyright 2019 Callino
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from odoo import api, models, fields
from odoo.addons.component.core import Component
from odoo.addons.queue_job.job import job, related_action

_logger = logging.getLogger(__name__)


class MagentoProductProduct(models.Model):
    _inherit = 'magento.product.product'
    
    attribute_set_id = fields.Many2one('magento.product.attributes.set',
                                       string='Attribute set')
    visibility = fields.Selection([
        ('1', 'Einzel nicht sichtbar'),
        ('4', 'Katalog, Suche'),
    ], string="Visibility", default='4')
    
    @api.multi
    @job(default_channel='root.magento')
    @related_action(action='related_action_unwrap_binding')
    def sync_to_magento(self):
        for binding in self:
            binding.with_delay().run_sync_to_magento()

    @api.multi
    @related_action(action='related_action_unwrap_binding')
    @job(default_channel='root.magento')
    def run_sync_to_magento(self):
        self.ensure_one()
        with self.backend_id.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            return exporter.run(self)


class ProductProductAdapter(Component):
    _inherit = 'magento.product.product.adapter'
    _magento2_name = 'product'

    def _get_id_from_create(self, result, data=None):
        # Products do use the sku as external_id - but we also need the id - so do return the complete data structure
        return result
