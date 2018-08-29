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

    
class ProductAttributeLine(models.Model):
    _inherit = 'product.attribute.line'
     
    attribute_text = fields.Char(string='Magento Text / Value',
                                    size=264)
    odoo_field_name = fields.Many2one(comodel_name='ir.model.fields', 
                                      related="attribute_id.odoo_field_name", 
                                      string="Odoo Field Name",)
    magento_attribute_type = fields.Selection(
        related="attribute_id.frontend_input")
    
    attribute_set_id = fields.Many2one(comodel_name="product.product",
                                       related="")
 


#     
#     
# 
# class ProductAttributeDetail(models.Model):
#     _name = 'product.attribute.detail'
# 
# 
# #     product_tmpl_id = fields.Many2one('product.template', 'Product Template', required=True)
# #     product_id = fields.Many2one('product.product', 'Product Product', required=False)    
# #     attribute_id = fields.Many2one('product.attribute','Select Attribute', required=True,
# #                                    domain=[('create_variant', '=', False)])
# #     
# #     attribute_text = fields.Char(string='Text / Value',size=264)
# #     
# #     
# #     _sql_constraints = [
# #         ('custom_attr_unique_product_uiq', 'unique(attribute_id,product_tmpl_id, product_id)', 'This attribute already have a value for this product !')
# #     ]
# 

# 
