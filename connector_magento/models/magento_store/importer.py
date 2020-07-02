# Copyright 2013-2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping


class StoreImportMapper(Component):
    _name = 'magento.store.mapper'
    _inherit = 'magento.import.mapper'
    _apply_on = 'magento.store'

    direct = [('name', 'name')]

    @mapping
    def website_id(self, record):
        binder = self.binder_for(model='magento.website')
        binding = binder.to_internal(record['website_id'])
        return {'website_id': binding.id}


class StoreImporter(Component):
    """ Import one Magento Store (create a sale.shop via _inherits) """

    _name = 'magento.store.importer'
    _inherit = 'magento.importer'
    _apply_on = 'magento.store'

    def _create(self, data):
        binding = super(StoreImporter, self)._create(data)
        self.backend_record.add_checkpoint(binding)
        return binding
