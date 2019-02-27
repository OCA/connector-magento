# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.addons.queue_job.job import identity_exact

IMPORT_DELTA_BUFFER = 30  # seconds
    
class MagentoWebsite(models.Model):
    _inherit = 'magento.website'
    
    @api.multi
    def import_attributes_set(self):
        for website in self:
            backend = website.backend_id
            self.env['magento.product.attributes.set'].with_delay(identity_key=identity_exact).import_batch(
                backend,
                filters={'magento_website_id': website.external_id}
            )

        return True
