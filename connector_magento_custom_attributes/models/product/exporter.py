# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import Component
from odoo.addons.connector.unit.mapper import mapping


class ProductProductExportMapper(Component):
    _inherit = 'magento.product.export.mapper'

    @mapping
    def names(self, record):
        storeview_id = self.work.storeview_id if hasattr(self.work, 'storeview_id') else False
        name = record.name
        if storeview_id:
            value_ids = record.\
            magento_attribute_line_ids.filtered(
                lambda att:
                    att.odoo_field_name.name == 'name'
                    and att.store_view_id == storeview_id
                    and att.attribute_id.create_variant != True
                    and (
                        att.attribute_text != False
                    )
                )
            name = value_ids[0].attribute_text
        return {'name': name}

    @mapping
    def get_custom_attributes(self, record):
        """
        Collect attributes to prensent it regarding to
        https://devdocs.magento.com/swagger/index_20.html
        catalogProductRepositoryV1 / POST 
        """

        customAttributes = []
        storeview_id = self.work.storeview_id if hasattr(self.work, 'storeview_id') else False
        magento_attribute_line_ids = record.magento_attribute_line_ids.filtered(
            lambda att: att.store_view_id.id == storeview_id and (
                        att.attribute_text or att.attribute_select.id or len(att.attribute_multiselect.ids) > 0))

        for values_id in magento_attribute_line_ids:
            """ Deal with Custom Attributes """            
            attributeCode = values_id.attribute_id.attribute_code
            if attributeCode == 'category_ids':
                # Ignore category here - will get set using the category_links
                continue
            value = values_id.attribute_text
            if values_id.magento_attribute_type == 'boolean':
                try:
                    value = int(values_id.attribute_text)
                except:
                    value = 0
            
            if values_id.magento_attribute_type in ['select',] and values_id.attribute_select.external_id:
                full_value = values_id.attribute_select.external_id
                value = full_value.split('_')[1]
            
            if values_id.attribute_id.nl2br:
                value = value.replace('\n', '<br />\n')
            customAttributes.append({
                'attribute_code': attributeCode,
                'value': value
                })     
        
        result = super(ProductProductExportMapper, self).get_custom_attributes(record)
        result['custom_attributes'].extend(customAttributes)
        return result
