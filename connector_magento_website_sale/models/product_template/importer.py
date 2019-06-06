# -*- coding: utf-8 -*-
# © 2019 Callino
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping
from odoo.addons.connector.exception import MappingError

_logger = logging.getLogger(__name__)


class ProductTemplateImportMapper(Component):
    _inherit = 'magento.product.template.import.mapper'

    @mapping
    def categories(self, record):
        if 'category_ids' not in record:
            return
        mag_categories = record.get('categories', record['category_ids'])
        binder = self.binder_for('magento.product.category')
        category_ids = []
        for mag_category_id in mag_categories:
            cat = binder.to_internal(mag_category_id, unwrap=False)
            if not cat:
                raise MappingError("The product category with "
                                   "magento id %s is not imported." %
                                   mag_category_id)
            category_ids.append(cat.public_categ_id.id)
        result = {'public_categ_ids': [(6, 0, category_ids)]}
        if self.options.for_create:
            result['categ_id'] = self.backend_record.default_category_id.id or None
        return result
