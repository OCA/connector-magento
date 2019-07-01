# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime, timedelta

IMPORT_DELTA_BUFFER = 30  # seconds


class MagentoBackend(models.Model):
    _inherit = 'magento.backend'

    @api.multi
    def export_product_catalog(self):
        import_start_time = datetime.now()
        # TODO make batchExporter class
        for backend in self:
            backend.check_magento_structure()
            domain = []
            if backend.export_products_from_date:
                domain = [('write_date', '>', backend.export_products_from_date)]
            mag_prods = self.env['magento.product.template'].search(domain)
            for mag_prod in mag_prods:
                mag_prod.sync_to_magento()
            next_time = import_start_time - timedelta(seconds=IMPORT_DELTA_BUFFER)
            next_time = fields.Datetime.to_string(next_time)
            backend.write({'export_products_from_date': next_time})
        return True

    product_synchro_strategy = fields.Selection([
            ('magento_first', 'Magento First'),
            ('odoo_first', 'Odoo First'),
        ],
        string='Product Update Strategy',
        help='Precise which strategy you want to update',
        default='magento_first'
    )
    export_products_from_date = fields.Datetime(
        string='Export products from date',
    )
    default_attribute_set_id = fields.Many2one('magento.product.attributes.set', string="Default Attribute Set id")

