# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping


class PartnerImportMapper(Component):
    _inherit = 'magento.partner.import.mapper'

    @mapping
    def names(self, record):
        parts = [part for part in (record['firstname'],
                                   record.get('middlename')) if part]
        values = {'firstname': ' '.join(parts),
                  'lastname': record['lastname']}
        return values


class AddressImportMapper(Component):
    _inherit = 'magento.address.import.mapper'

    @mapping
    def names(self, record):
        parts = [part for part in (record['firstname'],
                                   record.get('middlename')) if part]
        values = {'firstname': ' '.join(parts),
                  'lastname': record['lastname']}
        return values
