# -*- coding: utf-8 -*-
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
