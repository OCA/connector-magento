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
        if binding._name == 'magento.product.product':
            if binding.product_tmpl_id.magento_bind_ids:
                for tmpl_field in self.env['product.template']._fields.keys():
                    # Do not raise error when key is missing
                    data.pop(tmpl_field, False)
        return super(ProductImporter, self)._update(binding, data)
