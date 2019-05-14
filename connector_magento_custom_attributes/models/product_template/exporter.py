# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


import odoo
from datetime import datetime

from odoo.addons.component.core import Component
from odoo.addons.connector.unit.mapper import mapping, only_create
from odoo.addons.queue_job.job import identity_exact
from odoo.addons.connector.exception import MappingError
from slugify import slugify

from odoo.addons.connector_magento.components.backend_adapter import MAGENTO_DATETIME_FORMAT



class ProductTemplateExportMapper(Component):
    _inherit = 'magento.product.template.export.mapper'

    @mapping
    def names(self, record):
        storeview_id = self.work.storeview_id if hasattr(self.work, 'storeview_id') else False

        name = record.name
        if storeview_id:
            value_ids = record.\
            magento_template_attribute_value_ids.filtered(
                lambda att: 
                    att.odoo_field_name.name == 'name'
                    and att.store_view_id.id == storeview_id.id
                    and not att.attribute_id.create_variant
                    and att.attribute_text
                )
            name = value_ids[0].attribute_text if value_ids else record.name
        return {'name': name}
    
    @mapping
    def get_common_attributes(self, record):
        """
        Collect attributes to prensent it regarding to
        https://devdocs.magento.com/swagger/index_20.html
        catalogProductRepositoryV1 / POST 
        """
        
        customAttributes = []
        storeview_id = self.work.storeview_id if hasattr(self.work, 'storeview_id') else False
        magento_attribute_value_ids = record.\
            magento_template_attribute_value_ids.filtered(
                lambda att: 
                    att.attribute_id.is_pivot_attribute != True
                    and att.attribute_id.create_variant != True
                    and (
                        att.attribute_text != False
                        or
                        att.attribute_select.id != False
                        or 
                        len(att.attribute_multiselect.ids) > 0
                    )
            )
            
        
        for values_id in magento_attribute_value_ids:
            if not storeview_id and values_id.store_view_id.id != False:
                #Don't keep the value is no store view
                continue 
            if storeview_id and not values_id.store_view_id.id != storeview_id.id:
                continue
                
            """ Deal with Custom Attributes """            
            attributeCode = values_id.attribute_id.attribute_code
            value = values_id.attribute_text
            if values_id.magento_attribute_type == 'boolean':
                try:
                    value = int(values_id.attribute_text)
                except:
                    value = 0
            
            if values_id.magento_attribute_type in ['select',] and \
                    values_id.attribute_select.external_id != False:
                full_value = values_id.attribute_select.external_id
                value = full_value.split('_')[1]
            
            if values_id.magento_attribute_type in ['multiselect',] :
                value=[]
                for v in values_id.attribute_multiselect:
                    full_value = v.external_id
                    value.append(full_value.split('_')[1])
            
            
            customAttributes.append({
                'attribute_code': attributeCode,
                'value': value
                })     
        
        att_lines = record.magento_template_attribute_line_ids.filtered(
            lambda l: 
                    l.magento_attribute_id.create_variant == True
                    and l.magento_attribute_id.is_pivot_attribute != True
            )
        
        value_ids = self.env['magento.product.attribute.value']
        for l in att_lines:
            value_ids |= l.magento_product_attribute_value_ids
        for value_id in value_ids:
                """ Deal with Attributes in the 'variant' part of Odoo"""
#             odoo_value_ids = values_id.magento_bind_ids.filtered(
#                 lambda m: m.backend_id == record.backend_id) 
#             for odoo_value_id in odoo_value_ids:
                attributeCode = value_id.magento_attribute_id.attribute_code
                value = value_id.external_id.split('_')[1]
                customAttributes.append({
                    'attributeCode': attributeCode,
                    'value': value
                    })            
            
        result = {'customAttributes': customAttributes}
        return result   
