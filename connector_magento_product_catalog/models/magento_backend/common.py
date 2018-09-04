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
    
    
    @api.multi
    def export_product_product_catalog(self):
        for backend in self:
            backend.check_magento_structure()
            backend.website_ids.export_product_product_catalog()
        return True
    
    
    product_synchro_strategy = fields.Selection(
        [('magento_first', 'Magento First'),
        ('odoo_first', 'Odoo First'),
         ],
        string='Product Update Strategy',
        help='Precise which strategy you want to update',
        default='magento_first'
        )


