# -*- coding: utf-8 -*-
# Copyright 2018 Akretion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging

from odoo.addons.component.core import Component
# from odoo.addons.connector.components.mapper import mapping
# from odoo.addons.connector.exception import MappingError, InvalidDataError

_logger = logging.getLogger(__name__)


class ProductImporter(Component):
    _inherit = 'magento.product.product.importer'

    def _update(self, binding, data):
        """ Update an OpenERP record """
        # special check on data before import
        self._validate_data(data)

        # custom: remove template fields if product contained in a configurable
        magento_tmpl = self.env['magento.product.template'].search([
            ('odoo_id', '=', binding.odoo_id.product_tmpl_id)
        ], limit=1)
        if magento_tmpl:
            for tmpl_field in self.env['product.template']._fields.keys():
                data.pop(tmpl_field)
        # end custom

        binding.with_context(connector_no_export=True).write(data)
        _logger.debug('%d updated from magento %s', binding, self.external_id)
        return
