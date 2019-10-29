# -*- coding: utf-8 -*-
# Copyright <YEAR(S)> <AUTHOR(S)>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from odoo import api, models
from odoo.addons.component.core import Component
from odoo.addons.queue_job.job import job, related_action

_logger = logging.getLogger(__name__)


class MagentoProductCategory(models.Model):
    _inherit = 'magento.product.category'
    
    @api.multi
    def sync_to_magento(self):
        self.ensure_one()
        with self.backend_id.work_on(self._name) as work:
            usage = 'record.exporter'
            exporter = work.component(usage=usage)
            return exporter.run(self)

    @job(default_channel='root.magento')
    @related_action(action='related_action_unwrap_binding')
    @api.multi
    def export_category(self, fields=None):
        """ Export a category. """
        self.ensure_one()
        with self.backend_id.work_on(self._name) as work:
            usage = 'record.exporter'
            if self.backend_id.product_synchro_strategy == 'magento_first':
                usage = 'record.importer'
            exporter = work.component(usage=usage)
            return exporter.run(self)

    @job(default_channel='root.magento')
    @related_action(action='related_action_unwrap_binding')
    @api.multi
    def update_positions(self):
        if self.backend_id.product_synchro_strategy == 'magento_first':
            return
        for mcategory in self:
            # Start position update
            mtemplates = self.env['magento.product.template'].search([
                ('public_categ_ids', 'in', mcategory.public_categ_id.id),
                ('backend_id', '=', mcategory.backend_id.id),
            ])
            mproducts = self.env['magento.product.product'].search([
                ('public_categ_ids', 'in', mcategory.public_categ_id.id),
                ('backend_id', '=', mcategory.backend_id.id),
            ])
            with self.backend_id.work_on(self._name) as work:
                exporter = work.component(usage='position.exporter')
                for mtemplate in mtemplates:
                    if mtemplate.external_id:
                        exporter.run(mtemplate, mcategory=mcategory)
                for mproduct in mproducts:
                    if mproduct.external_id:
                        exporter.run(mproduct, mcategory=mcategory)


class ProductCategoryAdapter(Component):
    _inherit = 'magento.product.category.adapter'
    _magento2_name = 'category'

    def move_category(self, category_id, source_id, target_id):
        if self.backend_id.product_synchro_strategy == 'magento_first':
            return
        if self.work.magento_api._location.version == '2.0':
            return self._call("categories/%s/move" % category_id, {
                "parentId": int(source_id),
                "afterId": int(target_id)
            }, storeview=None, http_method="put")

    def update_category_position(self, category_id, sku, position):
        if self.backend_id.product_synchro_strategy == 'magento_first':
            return
        if self.work.magento_api._location.version == '2.0':
            res = self._call('categories/%s/products' % category_id, {
              "productLink": {
                "sku": sku,
                "position": position,
                "category_id": category_id,
                "extension_attributes": {}
              }
            }, http_method="post")
            return res
