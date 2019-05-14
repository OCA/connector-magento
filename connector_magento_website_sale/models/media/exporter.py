# -*- coding: utf-8 -*-
# Copyright 2019 Callino
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import Component
from odoo.addons.connector.unit.mapper import mapping


class ProductMediaExportMapper(Component):
    _inherit = 'magento.product.media.export.mapper'

    @mapping
    def get_content(self, record):
        if not record.type == 'product_image_ids':
            return super(ProductMediaExportMapper, self).get_content(record)
        return {'content': {
            'base64_encoded_data': record.odoo_id.image,
            'type': record.mimetype,
            'name': record.odoo_id.name,
        }}
