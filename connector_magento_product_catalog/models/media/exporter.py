# -*- coding: utf-8 -*-
# Copyright 2019 Callino
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import Component
from odoo.addons.connector.unit.mapper import mapping


class ProductMediaExporter(Component):
    _name = 'magento.product.media.exporter'
    _inherit = 'magento.exporter'
    _apply_on = ['magento.product.media']

    def _should_import(self):
        return False


class ProductMediaExportMapper(Component):
    _name = 'magento.product.media.export.mapper'
    _inherit = 'magento.export.mapper'
    _apply_on = ['magento.product.media']

    direct = [
        ('label', 'label'),
        ('disabled', 'disabled'),
        ('media_type', 'media_type'),
    ]
    
    @mapping
    def position(self, record):
        if record.position is False:
            return {}
        return {
            'position': record.position
        }

    @mapping
    def get_types(self, record):
        itypes = []
        if record.image_type_image:
            itypes.append('image')
        if record.image_type_small_image:
            itypes.append('small_image')
        if record.image_type_thumbnail:
            itypes.append('thumbnail')
        return {'types': itypes}

    @mapping
    def get_file(self, record):
        if self.options.for_create:
            # File is only supported on create
            return {'file': record.file}
        return None

    @mapping
    def get_id(self, record):
        if self.options.for_create:
            return None
        return {
            'id': record.external_id,
        }

    @mapping
    def get_content(self, record):
        return {'content': {
            'base64_encoded_data': record.magento_product_id.image,
            'type': record.mimetype,
            'name': record.file,
        }}
