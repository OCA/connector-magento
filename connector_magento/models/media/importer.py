# -*- coding: utf-8 -*-
# Copyright 2019 Callino
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging
from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping

_logger = logging.getLogger(__name__)


class ProductMediaImporter(Component):
    """ Import images for a record.

    Usually called from importers, in ``_after_import``.
    For instance from the products importer.
    """
    _name = 'magento.product.media.importer'
    _inherit = 'magento.importer'
    _apply_on = ['magento.product.media']
    _usage = 'product.media.importer'
    _magento_id_field = 'id'

    def _create_data(self, map_record, **kwargs):
        return map_record.values(for_create=True, product_binding=self.product_binding)

    def _update_data(self, map_record, **kwargs):
        return map_record.values(product_binding=self.product_binding)

    def _get_magento_data(self, binding=None):
        """ Return the raw Magento data for ``self.external_id`` """
        return self.backend_adapter.read(self.external_id, self.product_binding.external_id)

    def run(self, external_id, product_binding, force=False, binding=None):
        self.product_binding = product_binding
        return super(ProductMediaImporter, self).run(external_id, force, binding)


class ProductMediaMapper(Component):
    _name = 'magento.product.media.import.mapper'
    _inherit = 'magento.import.mapper'
    _apply_on = ['magento.product.media']

    direct = [
        ('label', 'label'),
        ('file', 'file'),
        ('position', 'position'),
        ('disabled', 'disabled'),
        ('media_type', 'media_type'),
    ]

    '''
    media_type=external-video:
            "extension_attributes": {
                "video_content": {
                    "media_type": "external-video",
                    "video_provider": "",
                    "video_url": "https://www.youtube.com/watch?v=osuhKVHZW2c",
                    "video_title": "Geoff Anderson Xylo Regenmantel",
                    "video_description": "Wasserdichter Regenmantel\r\n\r\nPijawetz Generalimport | Fachhandel Geoff Anderson\r\nwww.geoffanderson.de",
                    "video_metadata": ""
                }
            }    
    '''
    @mapping
    def mimetype(self, record):
        if 'mimetype' in record and record['mimetype']:
            return {'mimetype': record['mimetype']}
        else:
            return {'mimetype': 'image/jpeg'}

    @mapping
    def image_type(self, record):
        return {
            'image_type_image': 'image' in record['types'],
            'image_type_small_image': 'small_image' in record['types'],
            'image_type_thumbnail': 'thumbnail' in record['types'],
            'image_type_swatch': 'swatch_image' in record['types'],
        }

    @mapping
    def product_id(self, record):
        if self.options.product_binding.odoo_id._name == 'product.product':
            return {
                'magento_product_id': self.options.product_binding.id,
            }
        else:
            return {
                'magento_product_tmpl_id': self.options.product_binding.id,
            }


    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}
