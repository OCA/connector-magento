# -*- coding: utf-8 -*-
# © 2019 Callino
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.component.core import Component


class ProductCategoryImporter(Component):
    _inherit = 'magento.product.category.importer'


class ProductCategoryImportMapper(Component):
    _inherit = 'magento.product.category.import.mapper'

