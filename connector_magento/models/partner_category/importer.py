# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.connector.components.mapper import mapping, only_create
from odoo.addons.component.core import Component


class PartnerCategoryBatchImporter(Component):
    """ Delay import of the records """
    _name = 'magento.partner.category.batch.importer'
    _inherit = 'magento.delayed.batch.importer'
    _apply_on = 'magento.res.partner.category'


class PartnerCategoryImportMapper(Component):
    _name = 'magento.partner.category.import.mapper'
    _inherit = 'magento.import.mapper'
    _apply_on = 'magento.res.partner.category'

    direct = [
        ('customer_group_code', 'name'),
        ('tax_class_id', 'tax_class_id'),
    ]

    @mapping
    def external_id(self, record):
        return {'external_id': record['customer_group_id']}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}

    @only_create
    @mapping
    def odoo_id(self, record):
        """ Will bind the category on a existing one with the same name."""
        existing = self.env['res.partner.category'].search(
            [('name', '=', record['customer_group_code'])],
            limit=1,
        )
        if existing:
            return {'odoo_id': existing.id}
