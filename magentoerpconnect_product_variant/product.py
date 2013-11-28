# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright 2013
#    Author: Guewen Baconnier - Camptocamp SA
#            Chafique Delli - Akretion
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
##############################################################################

from openerp.osv import orm
from openerp.addons.magentoerpconnect.backend import magento
from openerp.addons.magentoerpconnect.connector import get_environment
from openerp.addons.magentoerpconnect_catalog.product import ProductProductExport
from openerp.addons.magentoerpconnect.unit.backend_adapter import GenericAdapter
from openerp.addons.magentoerpconnect.unit.export_synchronizer import (
    export_record, 
    MagentoExporter,
    MagentoBaseExporter,
)
from openerp.addons.connector.queue.job import job
 

class magento_product(orm.Model):
    _inherit = 'magento.product.product'
    
    def product_type_get(self, cr, uid, context=None):
        selection=super(magento_product, self).product_type_get(cr, uid, context=context)
        if ('configurable', 'Configurable Product') not in selection:
            selection += [('configurable', 'Configurable Product')]
        return selection

    def default_get(self, cr, uid, fields_list, context=None):
        if context is None:
            context = {}
        vals = super(magento_product, self).default_get(cr, uid, fields_list, context=context)
        if context.get('is_display'):
            vals['product_type'] = 'configurable'
        return vals

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        product_id = super(magento_product, self).create(cr, uid, vals, context=context)
        product = self.browse(cr, uid, product_id, context=context)
        if product.is_display:
            product.write({'product_type': 'configurable'})
        return product_id
        

@magento
class ProductConfigurableExport(MagentoBaseExporter):
    _model_name = ['magento.product.product']

    def _should_import(self):
        return False

    def _export_dependencies(self):
        """ Export the dependencies for the product"""
        if not self.binding_record.magento_id:
            export_record(self.session, 'magento.product.product', binding_id)
        record = self.binding_record
        
        #Check and update configurable params
        super_attribute_adapter = self.get_connector_unit_for_model(GenericAdapter, 'magento.super.attribute')
        
        magento_attr_ids = []
        data = super_attribute_adapter.list(record.magento_id)
        res = {x['attribute_id']: x['product_super_attribute_id'] for x in data}
        attr_binder = self.get_binder_for_model('magento.product.attribute')
        for dimension in record.dimension_ids:
            if not record.openerp_id[dimension.name]:
                magento_attr_id = attr_binder.to_backend(
                        dimension.product_attribute_id.id, wrap=True)
                if magento_attr_id in res:
                    del res[magento_attr_id]
                else:
                    magento_attr_ids.append(magento_attr_id)
        for magento_attr_id in magento_attr_ids:
            super_attribute_adapter.set(self.binding_record.magento_id, magento_attr_id)
        for magento_attr_id, super_attribute_id in res.items():
            super_attribute_adapter.remove(super_attribute_id)

        #Export simple product if necessary
        for product in record.display_for_product_ids:
            binding_id = self.session.search(self.model._name, [
                ['openerp_id', '=', product.id],
                ['backend_id', '=', self.backend_record.id]
            ])
            if binding_id:
                if not self.binder.to_backend(binding_id[0]):
                    export_record(self.session, 'magento.product.product', binding_id[0])
            elif self.backend_record.export_simple_product_on_fly:
                vals = self._prepare_magento_binding()
                binding_id = self.session.create('magento.product.product', vals)
                export_record(self.session, 'magento.product.product', binding_id)

    def _prepare_magento_binding(self, product):
        return {
            'backend_id': self.backend_record.id,
            'openerp_id': product.id,
            'name': product.name,
            'visibility': 1,
        }

    def _run(self, fields):
        self._export_dependencies()
        display_link_adapter = self.get_connector_unit_for_model(GenericAdapter, 'magento.configurable.link')

        record = self.binding_record
        
        res = display_link_adapter.list(self.magento_id)
        linked_product_ids = [x['product_id'] for x in res]
        product_ids_to_link = []
        for product in record.display_for_product_ids:
            magento_id = self.binder.to_backend(product.id, wrap=True)
            if magento_id in linked_product_ids:
                linked_product_ids.remove(magento_id)
            else:
                product_ids_to_link.append(magento_id)
        if product_ids_to_link:
            display_link_adapter.add(self.magento_id, product_ids_to_link)
        if linked_product_ids:
            display_link_adapter.remove(self.magento_id, linked_product_ids)


@job
def export_product_configurable(session, model_name, record_id, fields=None):
    """ Export the configuration for the configurable product. """
    product = session.browse(model_name, record_id)
    backend_id = product.backend_id.id
    env = get_environment(session, model_name, backend_id)
    configurable_exporter = env.get_connector_unit(ProductConfigurableExport)
    return configurable_exporter.run(record_id, fields)


@magento(replacing=ProductProductExport)
class ProductProductExport(ProductProductExport):
    _model_name = ['magento.product.product']

    def _should_import(self):
        if self.binding_record.is_display:
            return False

    def _after_export(self):
        """ Export the link for the configurable product"""
        if self.binding_record.is_display:
            export_product_configurable.delay(self.session, 'magento.product.product',
                                       self.binding_record.id,
                                       fields=['display_for_product_ids'],
                                       priority=20)


@magento
class ProductSuperAttributAdapter(GenericAdapter):
    _model_name = ['magento.super.attribute']
    _magento_model = 'ol_catalog_product_link'
       
    def set(self, magento_conf_id, magento_attribute_id):
        """ Set Configurables Attributes """
        return self._call('%s.setSuperAttributeValues'% self._magento_model,
                         [magento_conf_id, magento_attribute_id])
    
    def unlink(self, magento_id):
        """ Set Configurables Attributes """
        return self._call('%s.removeSuperAttribute'% self._magento_model,
                          [magento_id])
 
    def list(self, magento_conf_id):
        """ Set Configurables Attributes """
        return self._call('%s.listSuperAttributes'% self._magento_model,
                          [magento_conf_id])


@magento
class ProductConfigurableLinkAdapter(GenericAdapter):
    _model_name = ['magento.configurable.link']
    _magento_model = 'ol_catalog_product_link'
 
    def add(self, magento_conf_id, magento_product_ids):
        """ Add the product linked to the configurable """
        return self._call('%s.assign'% self._magento_model,
                          [magento_conf_id, magento_product_ids])

    def remove(self, magento_conf_id, magento_product_ids):
        """ Remove an existing link between products and a configurable """
        return self._call('%s.remove'% self._magento_model,
                          [magento_conf_id, magento_product_ids])

    def list(self, magento_conf_id):
        """ List the product linked to the configurable """
        return self._call('%s.list'% self._magento_model,
                          [magento_conf_id])
