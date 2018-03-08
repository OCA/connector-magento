# -*- coding: utf-8 -*-
# Copyright 2017 Akretion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


from odoo.addons.component.core import Component


class ConfigurableImporter(Component):
    _name = 'magento.product.configurable.importer'
    _inherit = 'magento.importer'
    _apply_on = ['magento.product.configurable']

    def run(self, record, force=False):
        filters = {'record': record}
        self.env['magento.product.attribute'].import_batch(
            self.backend_record,
            filters,
        )
        self.env['magento.product.attribute.line'].import_batch(
            self.backend_record,
            filters,
        )
