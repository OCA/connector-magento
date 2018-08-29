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

    
class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    attribute_set_id = fields.Many2one('magento.product.attributes.set', string='Attribute set')

    
    attribute_line_ids = fields.One2many('product.attribute.line', 'product_tmpl_id', string='Product Attributes',
                                         domain=[('attribute_id.create_variant', '=', True)] 
                                         )
      
    magento_attribute_line_ids = fields.One2many('product.attribute.line', 'product_tmpl_id', string='Magento Simple Product Attributes',
                                         domain=[('attribute_id.create_variant', '=', False)] 
                                         )
    
    
    
    #TODO: From now, as the mammping is hold by the product, no multi magento instance is supported
    # Has to be improved
    
    def check_field_mapping(self, field, vals):
        #Check if the Odoo Field has a matching attribute in Magento
        # Return an appropriate dictionnary
        att_id = None
        att_ids = self.env['magento.product.attribute'].search(
            [('odoo_field_name', '=', field),('options', '=', False)])
         
#         if len(att_ids)>0 :
#             att_id = att_ids[0].id
#             if 'magento_attribute' in vals and len(vals['magento_attribute']) >0:
#                 key_found = False  
#                 for key_dic in vals['magento_attribute']:
#                     if key_dic[2]['attribute_color'] == att_id:
#                         key_found = True
#                         key_dic[2]['attribute_text'] = vals[field]
#                 if not key_found:
#                     vals['magento_attribute'].append(
#                     (0, False, {
#                         'attribute_color': att_id,
#                         'attribute_text'  : vals[field]      
#                 }))
#             else:
#                 vals.update({'magento_attribute':[]})
#                 att_exists = self.magento_attribute.filtered(lambda a: a.attribute_color.id == att_id)
#                  
#                  
#                 if len(att_exists) ==0 :
#                     mode = 0
#                     mode_id = False 
#                 else:
#                     att_exists.unlink()
#                     mode = 0
#                     mode_id = False
#                          
#                 vals['magento_attribute'].append(
#                     (mode, mode_id, {
#                         'attribute_color': att_id,
#                         'attribute_text'  : vals[field]      
#                 }))
         
    
    
    
    def check_attribute_mapping(self, attr):
        #Check if the attribute modified has a matching field in Odoo
        # @attr : Tuple coming from a create / write method
        # Return a dict with field and its value in the proper format
        # http://www.odoo.com/documentation/10.0/reference/orm.html#model-reference ( CRUD part)
        if attr[0] == 0 :
            #Pure Added =>
            attribute_id = attr[2]['attribute_id']
            odoo_field_name = attr[2]['odoo_field_name']
        elif attr[0] == 1 : #Update
            detail = self.env['product.attribute.detail'].search([('id', '=', attr[1])])
            field = detail.attribute_color.id
        else:
            field = 0
             
         
        odoo_field_ids = self.env['magento.product.attribute'].search([
            ('odoo_field_name', '=', odoo_field_name),
            ('odoo_id', '=', attribute_id)
            ])
        #TODO: Imporve and deal with multiple Magento Instance
        if len(odoo_field_ids) == 1 :
            return {odoo_field_ids[0].odoo_field_name.name : attr[2]['attribute_text']}
        return None
    
    
    
    @api.multi
    def write(self, vals):
        org_vals = vals.copy()
        for key in org_vals:
            att_field = None
            odoo_field = None
            #Store attributes modes for choosing it 
            attributes_mode = {}
             
            if key == 'magento_attribute_line_ids':
                #If magento attribute, find the matching field if exists
                for key_att in org_vals['magento_attribute_line_ids']:                     
                    odoo_field = self.check_attribute_mapping(key_att)
                    if not odoo_field: continue
                    vals.update(odoo_field)
            else:
                #if 'magento_attribute' in org_vals :
#                 att_field = self.check_field_mapping(key, vals)
                _logger.info('WIP No updates')
 
        return super(ProductProduct, self).write(vals)                    

     
