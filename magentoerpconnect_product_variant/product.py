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

from openerp.osv import orm, fields
from openerp.addons.magentoerpconnect.backend import magento
from openerp.addons.magentoerpconnect.connector import get_environment
from openerp.addons.magentoerpconnect_catalog import product
from openerp.addons.magentoerpconnect.unit.backend_adapter import GenericAdapter
from openerp.addons.magentoerpconnect.unit.export_synchronizer import (
    export_record,
    MagentoBaseExporter,
    MagentoExporter)
from openerp.addons.connector.queue.job import job
from openerp.addons.connector.connector import ConnectorUnit


class ProductProduct(orm.Model):
    _inherit = 'product.product'

    def _prepare_create_magento_auto_binding(self, cr, uid, product,
                                             backend_id, context=None):
        res = super(ProductProduct, self)._prepare_create_magento_auto_binding(
            cr, uid, product, backend_id, context=context)
        if product.is_multi_variants and not product.is_display:
            res['visibility'] = '1'
        return res


class MagentoProduct(orm.Model):
    _inherit = 'magento.product.product'

    def product_type_get(self, cr, uid, context=None):
        selection = super(MagentoProduct, self).product_type_get(
            cr, uid, context=context)
        if ('configurable', 'Configurable Product') not in selection:
            selection += [('configurable', 'Configurable Product')]
        return selection

    def default_get(self, cr, uid, fields_list, context=None):
        if context is None:
            context = {}
        vals = super(MagentoProduct, self).default_get(
            cr, uid, fields_list, context=context)
        if context.get('is_display'):
            vals['product_type'] = 'configurable'
        return vals

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        product_id = super(MagentoProduct, self).create(
            cr, uid, vals, context=context)
        product = self.browse(cr, uid, product_id, context=context)
        if product.is_display:
            product.write({'product_type': 'configurable'})
        return product_id

    _columns = {
        'mag_super_attr_ids': fields.one2many(
            'magento.super.attribute', 'mag_product_display_id',
            string="Magento Bindings"),
    }


class MagentoSuperAttribute(orm.Model):
    _name = 'magento.super.attribute'
    _description = "Magento super attribute"
    _inherit = 'magento.binding'

    _columns = {
        'mag_product_display_id': fields.many2one('magento.product.product',
                                                  'Magento Product Id',
                                                  required=True,
                                                  ondelete='cascade',
                                                  select=True),
        'attribute_id': fields.many2one('attribute.attribute',
                                        'Product Attribute Id',
                                        required=True,
                                        ondelete='cascade',
                                        select=True),
    }


@magento
class ProductConfigurablePriceExporter(ConnectorUnit):
    _model_name = ['magento.product.product']

    def _export_super_attribute_price(self, binding):
        """ Export the price of super attribute for the configurable product"""
        return


@magento
class ProductConfigurableExporter(MagentoBaseExporter):
    _model_name = ['magento.product.product']

    def create_super_attribute(self, record, magento_id, bind_attribute):
        result = self.session.create(
            'magento.super.attribute', {
                'backend_id': self.backend_record.id,
                'magento_id': magento_id,
                'mag_product_display_id': record.id,
                'attribute_id': bind_attribute.openerp_id.id,
            })
        return result

    def _export_dependencies(self):
        """ Export the dependencies for the product"""
        record = self.binding_record
        if not record.magento_id:
            export_record(self.session, 'magento.product.product', record.id)

        #Check and update configurable params
        super_attribute_adapter = self.get_connector_unit_for_model(
            GenericAdapter, 'magento.super.attribute')
        magento_attr_ids = []
        data = super_attribute_adapter.list(record.magento_id)
        res = {x['attribute_id']: x['product_super_attribute_id'] for x in data}
        attr_binder = self.get_binder_for_model('magento.product.attribute')
        storeview_binder = self.get_binder_for_model('magento.storeview')
        for dimension in record.dimension_ids:
            if not record.openerp_id[dimension.name]:
                magento_attr_id = attr_binder.to_backend(
                    dimension.id, wrap=True)
                if magento_attr_id in res:
                    magento_id = res[magento_attr_id]
                    super_attr_binder = self.get_binder_for_model(
                        'magento.super.attribute')
                    bind_super_attribute_id = super_attr_binder.to_openerp(
                        res[magento_attr_id])
                    if not bind_super_attribute_id:
                        bind_attribute_id = attr_binder.to_openerp(
                            magento_attr_id)
                        bind_attribute = self.session.browse(
                            'magento.product.attribute', bind_attribute_id)
                        self.create_super_attribute(
                            record, magento_id, bind_attribute)
                    # we remove the attribute from the list of the existing
                    # super attribute in magento
                    # At the end of the process we will delete in magento
                    # the non existing one in Odoo
                    del res[magento_attr_id]
                else:
                    magento_attr_ids.append(magento_attr_id)
        for magento_attr_id in magento_attr_ids:
            bind_attribute_id = attr_binder.to_openerp(magento_attr_id)
            bind_attribute = self.session.browse(
                'magento.product.attribute', bind_attribute_id)
            labels = {}
            storeview_ids = self.session.search(
                'magento.storeview',
                [('backend_id', '=', self.backend_record.id)])
            for storeview in self.session.browse('magento.storeview',
                                                 storeview_ids):
                magento_storeview_id = storeview_binder.to_backend(storeview.id)
                ctx = self.session.context.copy()
                if storeview.lang_id:
                    ctx['lang'] = storeview.lang_id.code
                with self.session.change_context(ctx):
                    attribute = self.session.browse(
                        'attribute.attribute', bind_attribute.openerp_id.id)
                    labels[magento_storeview_id] = attribute.field_description
            magento_id = super_attribute_adapter.create(
                self.binding_record.magento_id, magento_attr_id, '0', labels)
            self.create_super_attribute(record, magento_id, bind_attribute)

        # some dimension can be remove on Odoo if there still exist
        # in magento we remove the super attribute
        for magento_attr_id, super_attribute_id in res.items():
            super_attribute_adapter.unlink(super_attribute_id)

        #Export simple product if necessary
        for variant in record.display_for_product_ids:
            for binding in variant.magento_bind_ids:
                if binding.backend_id.id == record.backend_id.id:
                    product_exporter = self.get_connector_unit_for_model(
                        MagentoExporter, 'magento.product.product')
                    binding_extra_vals = {}
                    product_exporter._export_dependency(
                        binding,
                        'magento.product.product',
                        'openerp.addons.magentoerpconnect.unit'
                        '.export_synchronizer.MagentoExporter',
                        'magento_bind_ids',
                        binding_extra_vals)

    def _prepare_magento_binding(self, product):
        return {
            'backend_id': self.backend_record.id,
            'openerp_id': product.id,
            'visibility': '1',
        }

    def _run(self, fields):
        self._export_dependencies()
        display_link_adapter = self.get_connector_unit_for_model(
            GenericAdapter, 'magento.configurable.link')

        record = self.binding_record

        res = display_link_adapter.list(self.magento_id)
        linked_product_ids = [x['product_id'] for x in res]
        product_ids_to_link = []
        for product_display in record.display_for_product_ids:
            magento_id = self.binder.to_backend(product_display.id, wrap=True)
            if not magento_id:
                continue
            if magento_id in linked_product_ids:
                linked_product_ids.remove(magento_id)
            else:
                product_ids_to_link.append(magento_id)
        if product_ids_to_link:
            display_link_adapter.add(self.magento_id, product_ids_to_link)
        if linked_product_ids:
            display_link_adapter.remove(self.magento_id, linked_product_ids)

    def _after_export(self):
        """ Export the price of super attribute for the configurable product"""
        binding = self.binding_record
        price_exporter = self.environment.get_connector_unit(ProductConfigurablePriceExporter)
        price_exporter._export_super_attribute_price(binding)


@job
def export_product_configurable(session, model_name, record_id, fields=None):
    """ Export the configuration for the configurable product. """
    product = session.browse(model_name, record_id)
    backend_id = product.backend_id.id
    env = get_environment(session, model_name, backend_id)
    configurable_exporter = env.get_connector_unit(ProductConfigurableExporter)
    return configurable_exporter.run(record_id, fields)


@magento(replacing=product.ProductProductConfigurableExport)
class ProductProductConfigurableExport(product.ProductProductConfigurableExport):
    _model_name = ['magento.product.product']

    def _export_configurable_link(self, binding):
        """ Export the link for the configurable product"""
        export_product_configurable.delay(
            self.session,
            'magento.product.product',
            binding.id,
            fields=['display_for_product_ids'],
            priority=20)


@magento
class ProductSuperAttributAdapter(GenericAdapter):
    _model_name = ['magento.super.attribute']
    _magento_model = 'ol_catalog_product_link'

    def create(self, magento_conf_id, magento_attribute_id, position, labels):
        """ Create Configurables Attributes """
        return self._call('%s.createSuperAttribute' % self._magento_model, [
            magento_conf_id,
            magento_attribute_id,
            position,
            labels,
        ])

    def unlink(self, magento_id):
        """ Remove Configurables Attributes """
        return self._call('%s.removeSuperAttribute' % self._magento_model,
                          [magento_id])

    def list(self, magento_conf_id):
        """ List Configurables Attributes """
        return self._call('%s.listSuperAttributes' % self._magento_model,
                          [magento_conf_id])

    def update(self, magento_super_attribute_id, data):
        """ Update Configurables Attributes """
        return self._call('%s.updateSuperAttributeValues' % self._magento_model,
                          (magento_super_attribute_id, data))


@magento
class ProductConfigurableLinkAdapter(GenericAdapter):
    _model_name = ['magento.configurable.link']
    _magento_model = 'ol_catalog_product_link'

    def add(self, magento_conf_id, magento_product_ids):
        """ Add the product linked to the configurable """
        return self._call('%s.assign' % self._magento_model,
                          [magento_conf_id, magento_product_ids])

    def remove(self, magento_conf_id, magento_product_ids):
        """ Remove an existing link between products and a configurable """
        return self._call('%s.remove' % self._magento_model,
                          [magento_conf_id, magento_product_ids])

    def list(self, magento_conf_id):
        """ List the product linked to the configurable """
        return self._call('%s.list' % self._magento_model,
                          [magento_conf_id])
