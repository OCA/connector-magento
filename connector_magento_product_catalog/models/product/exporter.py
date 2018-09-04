# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import xmlrpclib

import odoo
from datetime import datetime

from odoo import _
from odoo.addons.component.core import Component
from odoo.addons.queue_job.exception import NothingToDoJob
from odoo.addons.connector.unit.mapper import mapping

from odoo.addons.connector_magento.components.backend_adapter import MAGENTO_DATETIME_FORMAT


class BatchProductDefinitionExporter(Component):
    _name = 'magento.product.batch.exporter'
    _inherit = 'magento.delayed.batch.exporter'
    _apply_on = ['magento.product.product']
    _usage = 'batch.exporter'
<<<<<<< HEAD
=======


class ProductDefinitionExporter(Component):
    _name = 'magento.product.definition.exporter'
    _inherit = 'magento.exporter'
    _apply_on = ['magento.product.product']
    _usage = 'product.definition.exporter'
>>>>>>> branch '10.0-components-catalog-manager' of https://github.com/MindAndGo/connector-magento.git



class ProductDefinitionExporter(Component):
    _name = 'magento.product.product.exporter'
    _inherit = 'magento.exporter'
    _apply_on = ['magento.product.product']
#     _usage = 'product.definition.exporter'
    
    
    
    def _should_import(self):
        """ Before the export, compare the update date
        in Magento and the last sync date in Odoo,
        Regarding the product_synchro_strategy Choose 
        to whether the import or the export is necessary
        """
        assert self.binding
        if not self.external_id:
            return False
        sync = self.binding.sync_date
        if not sync:
            return True
        record = self.backend_adapter.read(self.external_id,
                                           attributes=['updated_at'])
        if not record['updated_at']:
            # in rare case it can be empty, in doubt, import it
            return True
        sync_date = odoo.fields.Datetime.from_string(sync)
        magento_date = datetime.strptime(record['updated_at'],
                                         MAGENTO_DATETIME_FORMAT)
        if self.backend_record.product_synchro_strategy == 'magento_first':
            return sync_date < magento_date
        else:
            return sync_date > magento_date
    
    
    def _delay_export(self):
        """ Schedule an import of the record.

        Adapt in the sub-classes when the model is not imported
        using ``export_record``.
        """
        # force is True because the sync_date will be more recent
        # so the import would be skipped
        assert self.external_id
        self.binding.with_delay().export_record(self.backend_record)


    def run(self, binding, *args, **kwargs):
        """ Run the synchronization

        :param binding: binding record to export
        """
        self.binding = binding

        self.external_id = self.binder.to_external(self.binding)
        try:
            should_import = self._should_import()
        except IDMissingInBackend:
            self.external_id = None
            should_import = False
        if should_import:
            if self.backend_record.product_synchro_strategy == 'magento_first':
                self._delay_import()
            else:
                self._delay_export()

        result = self._run(*args, **kwargs)

        self.binder.bind(self.external_id, self.binding)
        # Commit so we keep the external ID when there are several
        # exports (due to dependencies) and one of them fails.
        # The commit will also release the lock acquired on the binding
        # record
        if not odoo.tools.config['test_enable']:
            self.env.cr.commit()  # noqa

        self._after_export()
        return result
    
    
    
    
    
    def _get_atts_data(self, binding, fields):
        """
        Collect attributes to prensent it regarding to
        https://devdocs.magento.com/swagger/index_20.html
        catalogProductRepositoryV1 / POST 
        """
        
        customAttributes = []
        for values_id in binding.odoo_id.magento_attribute_line_ids:
            """ Deal with Custom Attributes """            
            attributeCode = values_id.attribute_id.name
            value = values_id.attribute_text
            customAttributes.append({
                'attributeCode': attributeCode,
                'value': value
                })
            
        for values_id in binding.odoo_id.attribute_value_ids:
            """ Deal with Attributes in the 'variant' part of Odoo"""
            attributeCode = values_id.attribute_id.name
            value = values_id.name
            customAttributes.append({
                'attributeCode': attributeCode,
                'value': value
                })
        result = {'customAttributes': customAttributes}
        return result

    
<<<<<<< HEAD
    def _should_import(self):
        """ Before the export, compare the update date
        in Magento and the last sync date in Odoo,
        Regarding the product_synchro_strategy Choose 
        to whether the import or the export is necessary
        """
        assert self.binding
        if not self.external_id:
            return False
        sync = self.binding.sync_date
        if not sync:
            return True
        record = self.backend_adapter.read(self.external_id,
                                           attributes=['updated_at'])
        if not record['updated_at']:
            # in rare case it can be empty, in doubt, import it
            return True
        sync_date = odoo.fields.Datetime.from_string(sync)
        magento_date = datetime.strptime(record['updated_at'],
                                         MAGENTO_DATETIME_FORMAT)
        if self.backend_record.product_synchro_strategy == 'magento_first':
            return sync_date < magento_date
        else:
            return sync_date > magento_date
    
    
    def _delay_import(self):
        """ Schedule an import/export of the record.

        Adapt in the sub-classes when the model is not imported
        using ``import_record``.
        """
        # force is True because the sync_date will be more recent
        # so the import would be skipped
        assert self.external_id
        if self.backend_record.product_synchro_strategy == 'magento_first':
            self.binding.with_delay().import_record(self.backend_record,
                                                self.external_id,
                                                force=True)
        else:
            self.binding.with_delay().export_record(self.backend_record)
    

class ProductProductExportMapper(Component):
    _name = 'magento.product.export.mapper'
    _inherit = 'magento.export.mapper'
    _apply_on = ['magento.product.product']

    direct = [
        ('name', 'name'),
        ('default_code', 'sku'),
        ('weight', 'weight'),
        ('product_type', 'typeId'),
    ]

    @mapping
    def attribute_set_id(self, record):        
        return {'attributeSetId' : record.attribute_set_id.external_id}

=======

class ProductProductExportMapper(Component):
    _name = 'magento.product.export.mapper'
    _inherit = 'magento.export.mapper'
    _apply_on = ['magento.product.product']

    direct = [
        ('name', 'name'),
        ('sku', 'default_code'),
    ]
# 
# 
>>>>>>> branch '10.0-components-catalog-manager' of https://github.com/MindAndGo/connector-magento.git
#     @changed_by('name', 'firstname', 'lastname')
    @mapping
    def names(self, record):
        
        return {}
#         if 'firstname' in record._fields:
#             firstname = record.firstname
#             lastname = record.lastname
#         else:
#             if ' ' in record.name:
#                 parts = record.name.split()
#                 firstname = parts[0]
#                 lastname = ' '.join(parts[1:])
#             else:
#                 lastname = record.name
#                 firstname = '-'
#         return {'firstname': firstname, 'lastname': lastname}


