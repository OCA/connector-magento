# Copyright 2013-2019 Camptocamp SA
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping


class MagentoStoreviewImportMapper(Component):
    _name = 'magento.storeview.mapper'
    _inherit = 'magento.import.mapper'
    _apply_on = 'magento.storeview'

    direct = [
        ('name', 'name'),
        ('code', 'code'),
        ('is_active', 'enabled'),
        ('sort_order', 'sort_order'),
        ('base_media_url', 'base_media_url'),
    ]

    @mapping
    def store_id(self, record):
        """ Bind to 'group_id' (Magento 1.x) or 'store_group_id' """
        binder = self.binder_for(model='magento.store')
        group_id = record.get('store_group_id') or record['group_id']
        binding = binder.to_internal(group_id)
        return {'store_id': binding.id}

    @mapping
    def lang_id(self, record):
        if self.collection.version == '2.0':
            lang = self.env['res.lang'].search(
                [('code', '=', record['locale'])])
            return {'lang_id': lang.id}


class StoreviewImporter(Component):
    """ Import one Magento Storeview """

    _name = 'magento.storeview.importer'
    _inherit = 'magento.importer'
    _apply_on = 'magento.storeview'

    def _create(self, data):
        binding = super(StoreviewImporter, self)._create(data)
        self.backend_record.add_checkpoint(binding)
        return binding
