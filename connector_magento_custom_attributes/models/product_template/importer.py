# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create
from odoo.addons.connector.exception import MappingError, InvalidDataError

_logger = logging.getLogger(__name__)


class ProductTemplateImportMapper(Component):
    _inherit = 'magento.product.template.import.mapper'

    @mapping
    def custom_attributes(self, record):
        """
        Usefull with catalog exporter module 
        has to be migrated
        """
        attribute_binder = self.binder_for('magento.product.attribute')
        magento_attribute_line_ids = []
        for attribute in record['custom_attributes']:
            mattribute = attribute_binder.to_internal(attribute['attribute_code'], unwrap=False, external_field='attribute_code')
            if not mattribute:
                raise MappingError("The product attribute %s is not imported." %
                                   mattribute.name)
            if mattribute.create_variant:
                # We do ignore attributes which do create a variant
                continue
            # Check for update or create
            mcav = self.options.binding.magento_template_attribute_line_ids.filtered(lambda line: line.attribute_id==mattribute and not line.store_view_id)
            if not mcav:
                vals = {
                    'attribute_id': mattribute.id,
                    'store_view_id': False,
                    'attribute_text': attribute['value']
                }
                magento_attribute_line_ids.append((0, False, vals))
            else:
                vals = {
                    'attribute_text': attribute['value']
                }
                magento_attribute_line_ids.append((1, mcav.id, vals))
        return {
            'magento_attribute_line_ids': magento_attribute_line_ids
        }
