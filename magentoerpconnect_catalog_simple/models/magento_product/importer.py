# -*- coding: utf-8 -*-
#
#    Author: Damien Crier
#    Copyright 2015 Camptocamp SA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from openerp.addons.magentoerpconnect.backend import magento
from openerp.addons.connector.unit.mapper import mapping
from openerp.addons.magentoerpconnect import product
from ..magento_attribute_set.importer import AttributeSetBatchImporter


@magento(replacing=product.WithCatalogProductImportMapper)
class ProductCatalogImportMapperFinalizerImporter(
        product.WithCatalogProductImportMapper):
    _model_name = 'magento.product.product'

    def _import_dependencies(self):
        """ Import the dependencies for the record"""
        record = self.magento_record
        env = self.environment
        # import attribute set
        if record.get('set'):
            binder = self.get_binder_for_model()
            set_id = record['set']
            if binder.to_openerp(set_id) is None:
                importer = env.get_connector_unit(AttributeSetBatchImporter)
                importer.run(set_id)

    @mapping
    def map_attribute_set(self, record):
        binder = self.binder_for(model='magento.attribute.set')
        binding_id = binder.to_openerp(record['set'])
        return {'attribute_set_id': binding_id}
