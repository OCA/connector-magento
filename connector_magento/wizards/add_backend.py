# -*- coding: utf-8 -*-
# Copyright <YEAR(S)> <AUTHOR(S)>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models, fields


class WizardModel(models.TransientModel):
    _name = "connector_magento.add_backend.wizard"

    @api.multi
    def get_default_object(self, model):        
        domain = []
        active_ids = self.env.context.get('active_ids', False)
        active_model = self.env.context.get('active_model', False)
        
        if not active_ids:
            return []
        domain.append(('id', 'in', active_ids))
        export = self.env[active_model]
 
        if active_model == 'product.template' :
           export = self.env['product.template'].search(domain)

        if active_model == 'product.product' :
           export = self.env['product.product'].search(domain)
#            tmp_ids = [p.product_tmpl_id for p in export_prod]     
#            export = self.env['product.template'].search([('id', 'in', tmp_ids)])
                 
        if active_model == 'product.category' :
           export = self.env['product.category'].search(domain)
        
        if active_model == model:
            return export     
        
        
    @api.multi
    def get_default_products(self):
        return self.get_default_object('product.product')
        
    @api.multi
    def get_default_category(self):
        return self.get_default_object('product.category')
        
    @api.multi 
    def check_backend_binding(self):                
        active_model = self.env.context.get('active_model', False)
        
        to_export_ids = None        
        
        dest_model = False
        
        if active_model in ['product.template']:
            to_export_ids = self.to_export_ids
            dest_model = 'magento.product.template'
        if active_model in ['product.product']:
            to_export_ids = self.to_export_ids
            dest_model = 'magento.product.product'
        elif active_model == 'product.category':
            to_export_ids = self.categ_to_export_ids
            dest_model = 'magento.product.category'
            
        export_ids = [p.id for p in to_export_ids]        
        
        odoo_prod_ids = self.env[dest_model].search(
                                    [('odoo_id', 'in', export_ids),
                                    ('backend_id', '=', self.backend_id.id)])
        prod_already_bind = [p.odoo_id.id for p in odoo_prod_ids]
        prod_already_bind_ids = self.env[active_model].search(
                                        [('id', 'in', prod_already_bind)])
        
        to_export = to_export_ids - prod_already_bind_ids
        
        for prod in to_export:
            vals = {'odoo_id': prod.id,
                    'external_id': prod.default_code,
                    'backend_id': self.backend_id.id                
                }
            self.env[dest_model].create(vals)
            
    backend_id = fields.Many2one(comodel_name='magento.backend', required=True)
    to_export_ids = fields.Many2many(string='Product Templates To export', 
                                     comodel_name='product.product', default=get_default_products)
    
    categ_to_export_ids = fields.Many2many(string='Category To export', 
                                           comodel_name='product.category', default=get_default_category)
    
    
    @api.multi
    def action_accept(self):
        self.ensure_one()
        self.check_backend_binding()
