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



class MagentoProductProduct(models.Model):
    _inherit = 'magento.product.product'
    
    @job(default_channel='root.magento')
    @api.multi
    def export_product(self, fields=None):
        """ Export the attributes configuration of a product. """
        self.ensure_one()
        with self.backend_id.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            return exporter.run(self)
    
    
    @api.multi
    def resync(self):
        raise NotImplementedError
    
class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    attribute_set_id = fields.Many2one('magento.product.attributes.set', string='Attribute set')

    magento_attribute_line_ids = fields.One2many(comodel_name='magento.custom.attribute.values', 
                                                 inverse_name='product_id', 
                                                 string='Magento Simple Custom Attributes Values',
                                        )
    
    
    #TODO: From now, as the mapping is hold by the product, no multi magento instance is supported
    # Has to be improved
    def check_field_mapping(self, field, vals):
        #Check if the Odoo Field has a matching attribute in Magento
        # Return an appropriate dictionnary
        
        att_id = 0
        odoo_field = self.env['ir.model.fields'].search([
                    ('name', '=', field),
                    ('model', '=', self._name)])[0]
        
        att_ids = self.env['magento.product.attribute'].search(
            [('odoo_field_name', '=', odoo_field.id or 0),])
         
        if len(att_ids)>0 :
            att_id = att_ids[0].id
            if 'magento_attribute_line_ids' in vals and len(vals['magento_attribute_line_ids']) >0:
                key_found = False  
                for key_dic in vals['magento_attribute_line_ids']:
                    if key_dic[2]['attribute_color'] == att_id:
                        key_found = True
                        key_dic[2]['attribute_text'] = vals[field]
                if not key_found:
                    vals['magento_attribute'].append(
                    (0, False, {
                        'attribute_color': att_id,
                        'attribute_text'  : vals[field]      
                }))
            else:
                vals.update({'magento_attribute_line_ids':[]})
                att_exists = self.magento_attribute_line_ids.filtered(
                            lambda a: a.attribute_id.id == att_id)
                
                if len(att_exists) ==0 :
                    mode = 0
                    mode_id = False 
                else:
                    att_exists.unlink()
                    mode = 0
                    mode_id = False
                          
                vals['magento_attribute_line_ids'].append(
                    (mode, mode_id, {
                        'attribute_id': att_id,
                        'attribute_text'  : vals[field]      
                }))
         
    
    def check_attribute_mapping(self, attr):
        #Check if the attribute modified has a matching field in Odoo
        # @attr : Tuple coming from a create / write method
        # Return a dict with field and its value in the proper format
        # http://www.odoo.com/documentation/10.0/reference/orm.html#model-reference ( CRUD part)
        
        odoo_field_name = 0
        attribute_id = 0
        
        if attr[0] == 0 :
            #Pure Added =>
            attribute_id = attr[2]['attribute_id']
            odoo_field_name = attr[2]['odoo_field_name']
        elif attr[0] == 1 : #Update
            detail = self.env['magento.custom.attribute.values'].search([('id', '=', attr[1])])
            odoo_field_name = detail.odoo_field_name.id
            attribute_id = detail.attribute_id.id
        
        odoo_field_ids = self.env['magento.product.attribute'].search([
            ('odoo_field_name', '=', odoo_field_name),
            ('odoo_field_name', '!=', False),
            ('id', '=', attribute_id)
            ])
        #TODO: Improve and deal with multiple Magento Instance
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
                att_field = self.check_field_mapping(key, vals)
                
 
        return super(ProductProduct, self).write(vals)                    

     
class ProductProductAdapter(Component):
    _inherit = 'magento.product.product.adapter'
    _apply_on = 'magento.product.product'

    _magento_model = 'catalog_product'
    _magento2_model = 'products'
    _magento2_search = 'products'
    _magento2_key = 'sku'
    _admin_path = '/{model}/edit/id/{id}'
    
    
    def _get_atts_data(self, binding):
        """
        Collect attributes to prensent it regarding to
        https://devdocs.magento.com/swagger/index_20.html
        catalogProductRepositoryV1 / POST 
        """
        
        customAttributes = []
        for values_id in binding.odoo_id.magento_attribute_line_ids:
            """ Deal with Custom Attributes """            
            attributeCode = values_id.attribute_id.name
            value = values_id.attribute_text
            customAttributes.append({
                'attributeCode': attributeCode,
                'value': value
                })
            
        for values_id in binding.odoo_id.attribute_value_ids:
            """ Deal with Attributes in the 'variant' part of Odoo"""
            attributeCode = values_id.attribute_id.name
            value = values_id.name
            customAttributes.append({
                'attributeCode': attributeCode,
                'value': value
                })
        result = {'customAttributes': customAttributes}
        return result
    
    
    def get_product_datas(self, data, saveOptions=True):
        main_datas = super(ProductProductAdapter, self).get_product_datas(data, saveOptions)
#         main_datas.update(self._get_atts_data(self.binding_))
        return main_datas
    
