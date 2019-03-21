# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping
from odoo.addons.connector.exception import MappingError


class AccountTaxBatchImporter(Component):
    """ Import the Magento Tax Classes.

    """
    _name = 'magento.account.tax.batch.importer'
    _inherit = 'magento.delayed.batch.importer'
    _apply_on = ['magento.account.tax']

    def _import_record(self, external_id, job_options=None):
        """ Delay a job for the import """
        super(AccountTaxBatchImporter, self)._import_record(
            external_id, job_options=job_options
        )

    def run(self, filters=None):
        """ Run the synchronization """
        if self.work.magento_api._location.version == '2.0':

            importer = self.component(usage='record.importer')
            mclasses = self.backend_adapter.search()

            for class_id in mclasses:
                importer.run(class_id)


class AccountTaxImporter(Component):
    _name = 'magento.account.tax.importer'
    _inherit = 'magento.importer'
    _apply_on = ['magento.account.tax']

    def _is_uptodate(self, binding):
        # TODO: Remove for production
        return False

    def _create(self, data):
        binding = super(AccountTaxImporter, self)._create(data)
        self.backend_record.add_checkpoint(binding)
        return binding


class AccountTaxImportMapper(Component):
    _name = 'magento.account.tax.import.mapper'
    _inherit = 'magento.import.mapper'
    _apply_on = 'magento.account.tax'

    direct = [
        ('class_name', 'class_name'),
        ('class_type', 'class_type'),
        ('class_id', 'external_id'),
    ]
    
    @mapping
    def odoo_id(self, record):
        # Just use the first tax class - user has to rework it in checkpoint !
        return {'odoo_id': self.env['account.tax'].search([], limit=1).id}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}
