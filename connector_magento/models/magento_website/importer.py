# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import _
from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping


class WebsiteImportMapper(Component):
    _name = 'magento.website.mapper'
    _inherit = 'magento.import.mapper'
    _apply_on = 'magento.website'

    direct = [('code', 'code'),
              ('sort_order', 'sort_order')]

    @mapping
    def name(self, record):
        name = record['name']
        if name is None:
            name = _('Undefined')
        return {'name': name}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}


class MagentoWebsiteImporter(Component):
    """ Import one Magento Website """

    _name = 'magento.website.record.importer'
    _inherit = 'magento.importer'
    _apply_on = ['magento.website']
