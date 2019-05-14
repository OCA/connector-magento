# -*- coding: utf-8 -*-
# Copyright 2019 Callino
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.h

from odoo.addons.component.core import Component
from odoo.addons.component_event import skip_if


class MagentoProductTemplateExportListener(Component):
    _inherit = 'magento.product.template.export.listener'

    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    def on_record_write(self, record, fields=None):
        if record.product_variant_count == 1:
            binding_ids = record.product_variant_ids[0].magento_bind_ids
        else:
            binding_ids = record.magento_bind_ids
        for binding in binding_ids:
            # First - do update the custom attribute values
            binding.recheck_field_mapping(record)
        super(MagentoProductTemplateExportListener, self).on_record_write(record, fields=fields)
