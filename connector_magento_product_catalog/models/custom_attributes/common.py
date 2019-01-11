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

    
class CustomAttribute(models.Model):
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
                                    size=264,
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
    

    @api.one
    @api.constrains('attribute_id')
    def check_attribute_id(self):
        
        # TODO: control if the attribute and the attribute set are coherent
        return 
        
    _sql_constraints = [
        ('custom_attr_unique_product_uiq', 'unique(attribute_id, product_id, backend_id)', 'This attribute already have a value for this product !')
    ]

