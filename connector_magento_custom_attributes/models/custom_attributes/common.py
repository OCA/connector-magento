# -*- coding: utf-8 -*-
# Copyright <YEAR(S)> <AUTHOR(S)>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import xmlrpclib
from odoo import api, models, fields
from odoo.addons.component.core import Component
from odoo.addons.queue_job.job import job, related_action
from odoo.addons.connector.exception import IDMissingInBackend

_logger = logging.getLogger(__name__)

    
class MagentoCustomAttribute(models.Model):
    _name = 'magento.custom.attribute.values'
    
     
    """
    This class deal with customs Attributes
    """
#     
    magento_product_id = fields.Many2one(comodel_name="magento.product.product",
                                string="Magento Product",
                                )
    
    product_id = fields.Many2one(comodel_name="product.product",
                                string="Product",
                                related="magento_product_id.odoo_id",
                                required=True)
 
    backend_id = fields.Many2one(comodel_name="magento.backend",
                                      string="Magento Backend",
                                      related="magento_product_id.backend_id"
                                      )
     
    attribute_id = fields.Many2one(comodel_name="magento.product.attribute",
                                      string="Magento Product Attribute",
                                      required=True,
#                                       domain=[('backend_id', '=', backend_id)]
                                      )
    
    magento_attribute_type = fields.Selection(
         related="attribute_id.frontend_input",
         store=True
        )
    
    attribute_text = fields.Char(string='Magento Text / Value',
                                    translate=True
                                    )
    
    attribute_select = fields.Many2one(string='Magento Select / Value',
                                    comodel_name="magento.product.attribute.value",
                                    domain=[('magento_attribute_type', '=', 'select')]
                                    )
    
    attribute_multiselect = fields.Many2many(string='Magento MultiSelect / Value',
                                    relation="magento_custom_attributes_rel",
                                    comodel_name="magento.product.attribute.value",
                                    domain=[('magento_attribute_type', '=', 'multiselect')]
                                    )
    
    
    odoo_field_name = fields.Many2one(
        comodel_name='ir.model.fields', 
        related="attribute_id.odoo_field_name", 
        string="Odoo Field Name",
        store=True) 
    
    store_view_id = fields.Many2one('magento.storeview')
    _sql_constraints = [
        ('magento_uniq', 'unique(backend_id, attribute_id, store_view_id, magento_product_id)',
         'A binding already exists with the same Magento ID.'),
    ]

    @api.model
    def create(self, vals):
        res = super(MagentoCustomAttribute,self).create(vals)
        res.check_attribute_id()
        return res
    
    
    @api.multi
    def write(self, vals):
        org_vals = vals.copy()
        res = super(MagentoCustomAttribute, self).write(vals)
        for cv in self:
            cv.check_attribute_id()
        return res

    @api.one
    @api.constrains('attribute_id')
    def check_attribute_id(self):
        self.ensure_one()
        res = self
        if 'no_update' in self._context and \
            self._context.get('no_update', False):
            return
        if res.odoo_field_name.id != False:
            odoo_field_name = res.odoo_field_name
            custom_vals = {
                    odoo_field_name.name: res.attribute_text,
            }
            if res.magento_attribute_type == 'boolean':
                custom_vals.update({
                    odoo_field_name.name: int(res.attribute_text),
                    })
            if res.magento_attribute_type == 'select':
                custom_vals.update({
                    odoo_field_name.name: res.attribute_select.odoo_id.id,
                    })
            if res.magento_attribute_type == 'multiselect':
                custom_vals.update({
                    odoo_field_name.name: [
                        (6, False, 
                         [s.odoo_id.id for s in res.attribute_multiselect])
                        ],
                    })
            
            res.product_id.with_context(no_update=True).write(custom_vals)
        
    _sql_constraints = [
        ('custom_attr_unique_product_uiq', 'unique(attribute_id, product_id, backend_id)', 'This attribute already have a value for this product !')
    ]

