# -*- coding: utf-8 -*-
from odoo import models, fields, api

class MagentoBackend(models.Model):
    _inherit = 'magento.backend'
    
    @api.multi
    def import_attributes_set(self):
        """ Import sale orders from all store views """
        for backend in self:
            backend.check_magento_structure()
            backend.website_ids.import_attributes_set()
        return True
    
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


