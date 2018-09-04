# -*- coding: utf-8 -*-
from odoo import models, fields, api
    
class MagentoWebsite(models.Model):
    _inherit = 'magento.website'
    
    @api.multi
    def import_attributes_set(self):
        for website in self:
            backend = website.backend_id
            self.env['magento.product.attributes.set'].with_delay().import_batch(
                backend,
                filters={'magento_website_id': website.external_id}
            )

        return True


    @api.multi
    def export_product_product_catalog(self):
        for website in self:
            backend = website.backend_id
            self.env['magento.product.product'].with_delay().export_batch(
                backend,
                filters={'magento_website_id': website.external_id}
            )

        return True




