# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping
from odoo import _


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
    
    def _must_skip(self):
        """ Hook called right after we read the data from the backend.

        If the method returns a message giving a reason for the
        skipping, the import will be interrupted and the message
        recorded in the job (if the import is called directly by the
        job, not by dependencies).

        If it returns None, the import will continue normally.

        :returns: None | str | unicode
        """
        if not self.magento_record :
            return _('The website is not properly defined')
