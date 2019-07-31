# -*- coding: utf-8 -*-
# Copyright 2019 Callino
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import _
from odoo.addons.component.core import Component
from odoo.addons.connector.unit.mapper import mapping
import os.path
import logging

_logger = logging.getLogger(__name__)


class ProductMediaExporter(Component):
    _name = 'magento.product.media.exporter'
    _inherit = 'magento.exporter'
    _apply_on = ['magento.product.media']

    def _should_import(self):
        return False

    def _update(self, data, storeview_code=None):
        """ Update an Magento record """
        assert self.external_id
        # We have to delete a recreate because of a bug in magento 2
        try:
            self.backend_adapter.delete(self.binding.external_id, self.binding)
        except:
            _logger.info("Got error on delete old media - ignore it")
        new_id = self.backend_adapter.create(data, self.binding)
        self.external_id = new_id

    def _run(self, fields=None):
        """ Flow of the synchronization, implemented in inherited classes"""
        assert self.binding

        if not self.external_id:
            fields = None  # should be created with all the fields

        if self._has_to_skip():
            return

        # export the missing linked resources
        self._export_dependencies()

        # prevent other jobs to export the same record
        # will be released on commit (or rollback)
        self._lock()

        map_record = self._map_data()

        if self.external_id:
            record = self._create_data(map_record, fields=fields)
            if not record:
                return _('Nothing to export.')
            self._update(record)
        else:
            record = self._create_data(map_record, fields=fields)
            if not record:
                return _('Nothing to export.')
            data = self._create(record)
            if not data:
                raise UserWarning('Create did not returned anything on %s with binding id %s', self._name, self.binding.id)
            self._update_binding_record_after_create(data)
        return _('Record exported with ID %s on Magento.') % self.external_id


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
        if record.image_type_swatch:
            itypes.append('swatch_image')
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
            'base64_encoded_data': record.magento_product_id.image if record.magento_product_id else record.magento_product_tmpl_id.image,
            'type': record.mimetype,
            'name': os.path.basename(record.file),
        }}
