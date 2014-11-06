# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright 2013
#    Author: Guewen Baconnier - Camptocamp SA
#            Augustin Cisterne-Kaasv - Elico-corp
#            David Béal - Akretion
#            Chafique Delli - Akretion
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

from openerp.osv import fields, orm
from openerp.addons.connector.unit.mapper import (mapping,
                                                  ExportMapper)
from openerp.addons.magentoerpconnect.unit.delete_synchronizer import (
    MagentoDeleteSynchronizer)
from openerp.addons.magentoerpconnect.unit.export_synchronizer import (
    MagentoTranslationExporter)
from openerp.addons.magentoerpconnect.backend import magento
from openerp.addons.connector.exception import MappingError
from openerp.addons.magentoerpconnect.unit.export_synchronizer import (
    export_record
)
import openerp.addons.magentoerpconnect.consumer as magentoerpconnect
from openerp.addons.connector.event import on_record_write
from openerp.addons.connector.connector import ConnectorUnit
from openerp.tools.translate import _
import logging
_logger = logging.getLogger(__name__)


class MagentoProductProduct(orm.Model):
    _inherit = 'magento.product.product'

    _columns = {
        'active': fields.boolean(
            'Active',
            help=("When a binding is unactivated, the product is delete from "
            "Magento. This allow to remove product from Magento and so "
            "to increase the perf on Magento side")),
        }

    #Automatically create the magento binding for each image
    def create(self, cr, uid, vals, context=None):
        mag_image_obj = self.pool['magento.product.image']
        mag_product_id = super(MagentoProductProduct, self).\
            create(cr, uid, vals, context=context)
        mag_product = self.browse(cr, uid, mag_product_id, context=context)
        if mag_product.backend_id.auto_bind_image:
            for image in mag_product.image_ids:
                mag_image_obj.create(cr, uid, {
                    'openerp_id': image.id,
                    'backend_id': mag_product.backend_id.id,
                }, context=context)
        return mag_product_id

    def write(self, cr, uid, ids, vals, context=None):
        if vals.get('active') is True:
            binding_ids = self.search(cr, uid, [
                ('active', '=', False),
            ], context=context)
            if len(binding_ids) > 0:
                raise orm.except_orm(
                    _('User Error'),
                    _('You can not reactivate the following binding ids: %s '
                      'please add a new one instead') % binding_ids)
        return super(MagentoProductProduct, self).\
            write(cr, uid, ids, vals, context=context)

    def unlink(self, cr, uid, ids, context=None):
        synchronized_binding_ids = self.search(cr, uid, [
            ('id', 'in', ids),
            ('magento_id', '!=', False),
        ], context=context)
        if synchronized_binding_ids:
            raise orm.except_orm(
                _('User Error'),
                _('This binding ids %s can not be remove as '
                  'the field magento_id is not empty.\n'
                  'Please unactivate it instead'))
        return super(MagentoProductProduct, self).unlink(
            cr, uid, ids, context=context)

    _defaults = {
        'active': True,
        }


class ProductProduct(orm.Model):
    _inherit = 'product.product'

    _columns = {
        'magento_inactive_bind_ids': fields.one2many(
            'magento.product.product',
            'openerp_id',
            domain=[('active', '=', False)],
            readonly=True,
            string='Magento Bindings',),
    }

    def _prepare_create_magento_auto_binding(self, cr, uid, product,
                                             backend_id, context=None):
        return {
            'backend_id': backend_id,
            'openerp_id': product.id,
            'visibility': '4',
            'status': '1',
        }

    def _get_magento_binding(self, cr, uid, product_id, backend_id, context=None):
        binding_ids = self.pool['magento.product.product'].search(cr, uid, [
            ('openerp_id', '=', product_id),
            ('backend_id', '=', backend_id),
        ], context=context)
        if binding_ids:
            return binding_ids[0]
        else:
            return None

    def automatic_binding(self, cr, uid, ids, sale_ok, context=None):
        backend_obj = self.pool['magento.backend']
        mag_product_obj = self.pool['magento.product.product']
        back_ids = backend_obj.search(cr, uid, [], context=context)
        products = self.browse(cr, uid, ids, context=context)
        for backend in backend_obj.browse(cr, uid, back_ids, context=context):
            if backend.auto_bind_product:
                for product in products:
                    binding_id = self._get_magento_binding(
                        cr, uid, product.id, backend.id, context=context)
                    if not binding_id and sale_ok:
                        vals = self._prepare_create_magento_auto_binding(
                            cr, uid, product, backend.id, context=context)
                        mag_product_obj.create(cr, uid, vals, context=context)
                    else:
                        mag_product_obj.write(cr, uid, binding_id, {
                            'status': '1' if sale_ok else '2',
                        }, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        super(ProductProduct, self).write(cr, uid, ids, vals, context=context)
        if vals.get('active', True) is False:
            for product in self.browse(cr, uid, ids, context=context):
                for bind in product.magento_bind_ids:
                    bind.write({'active': False})
        if 'sale_ok' in vals:
            self.automatic_binding(cr, uid, ids, vals['sale_ok'], context=context)
        return True

    def create(self, cr, uid, vals, context=None):
        product_id = super(ProductProduct, self).create(
            cr, uid, vals, context=context)
        product = self.browse(cr, uid, product_id, context=context)
        if product.sale_ok:
            self.automatic_binding(cr, uid, [product.id], True, context=context)
        return product_id

    def _check_uniq_magento_product(self, cr, uid, ids):
        cr.execute("""SELECT openerp_id
        FROM magento_product_product
        WHERE active=True
        GROUP BY backend_id, openerp_id
        HAVING count(id) > 1""")
        result = cr.fetchall()
        if result:
            raise orm.except_orm(
                _('User Error'),
                _('You can not have more than one active binding for '
                  'a product. Here is the list of product ids with a '
                  'duplicated binding : %s')
                % ", ".join([str(x[0]) for x in result]))
        return True

    _constraints = [(
        _check_uniq_magento_product,
        'Only one binding can be active',
        ['backend_id', 'openerp_id', 'active'],
        )]


@on_record_write(model_names=[
    'magento.product.product',
])
def delay_export(session, model_name, record_id, vals=None):
    if vals.get('active', True) == False:
        magentoerpconnect.delay_unlink(session, model_name, record_id)


@magento
class ProductProductDeleteSynchronizer(MagentoDeleteSynchronizer):
    """ Partner deleter for Magento """
    _model_name = ['magento.product.product']


@magento
class ProductProductConfigurableExport(ConnectorUnit):
    _model_name = ['magento.product.product']

    def _export_configurable_link(self, binding):
        """ Export the link for the configurable product"""
        return


@magento
class ProductProductExporter(MagentoTranslationExporter):
    _model_name = ['magento.product.product']

    @property
    def mapper(self):
        if self._mapper is None:
            self._mapper = self.get_connector_unit_for_model(
                ProductProductExportMapper)
        return self._mapper

    def _should_import(self):
        """Product are only edited on OpenERP Side"""
        return False

    def _create(self, data):
        """ Create the Magento record """
        # special check on data before export
        sku = data.pop('sku')
        attr_set_id = data.pop('attrset')
        product_type = data.pop('product_type')
        self._validate_data(data)
        return self.backend_adapter.create(product_type, attr_set_id, sku, data)

    def _export_dependencies(self):
        """ Export the dependencies for the product"""
        #TODO add export of category
        attribute_binder = self.get_binder_for_model('magento.product.attribute')
        option_binder = self.get_binder_for_model('magento.attribute.option')
        record = self.binding_record
        for group in record.attribute_group_ids:
            for attribute in group.attribute_ids:
                attribute_ext_id = attribute_binder.to_backend(
                    attribute.attribute_id.id, wrap=True)
                if attribute_ext_id:
                    options = []
                    if attribute.ttype == 'many2one' and record[attribute.name]:
                        options = [record[attribute.name]]
                    elif attribute.ttype == 'many2many':
                        options = record[attribute.name]
                    for option in options:
                        if not option_binder.to_backend(option.id, wrap=True):
                            ctx = self.session.context.copy()
                            ctx['connector_no_export'] = True
                            binding_id = self.session.pool['magento.attribute.option'].create(
                                self.session.cr, self.session.uid, {
                                    'backend_id': self.backend_record.id,
                                    'openerp_id': option.id,
                                    'name': option.name,
                                }, context=ctx)
                            export_record(self.session, 'magento.attribute.option', binding_id)

    def _after_export(self):
        """ Export the link for the configurable product"""
        binding = self.binding_record
        if binding.is_display:
            configurable_exporter = self.environment.get_connector_unit(ProductProductConfigurableExport)
            configurable_exporter._export_configurable_link(binding)


@magento
class ProductProductExportMapper(ExportMapper):
    _model_name = 'magento.product.product'

    #TODO FIXME
    # direct = [('name', 'name'),
    #           ('description', 'description'),
    #           ('weight', 'weight'),
    #           ('list_price', 'price'),
    #           ('description_sale', 'short_description'),
    #           ('default_code', 'sku'),
    #           ('product_type', 'type'),
    #           ('created_at', 'created_at'),
    #           ('updated_at', 'updated_at'),
    #           ('status', 'status'),
    #           ('visibility', 'visibility'),
    #           ('product_type', 'product_type')
    #           ]
    @mapping
    def all(self, record):
        return {'name': record.name,
                'description': record.description,
                'weight': record.weight,
                'price': record.lst_price,
                'short_description': record.description_sale,
                'type': record.product_type,
                'created_at': record.created_at,
                #'updated_at': record.updated_at,
                'status': record.status,
                'visibility': record.visibility,
                'product_type': record.product_type }

    @mapping
    def sku(self, record):
        sku = record.default_code
        if not sku:
            raise MappingError("The product attribute default code cannot be empty.")
        return {'sku': sku}

    @mapping
    def set(self, record):
        binder = self.get_binder_for_model('magento.attribute.set')
        set_id = binder.to_backend(record.attribute_set_id.id, wrap=True)
        return {'attrset': set_id}

    @mapping
    def updated_at(self, record):
        updated_at = record.updated_at
        if not updated_at:
            updated_at = '1970-01-01'
        return {'updated_at': updated_at}

    @mapping
    def website_ids(self, record):
        website_ids = []
        for website_id in record.website_ids:
            magento_id = website_id.magento_id
            website_ids.append(magento_id)
        return {'website_ids': website_ids}

    @mapping
    def category(self, record):
        categ_ids = []
        if record.categ_id:
            for m_categ in record.categ_id.magento_bind_ids:
                if m_categ.backend_id.id == self.backend_record.id:
                    categ_ids.append(m_categ.magento_id)

        for categ in record.categ_ids:
            for m_categ in categ.magento_bind_ids:
                if m_categ.backend_id.id == self.backend_record.id:
                    categ_ids.append(m_categ.magento_id)
        return {'categories': categ_ids}

    @mapping
    def get_product_attribute_option(self, record):
        result = {}
        option_binder = self.get_binder_for_model('magento.attribute.option')
        for group in record.attribute_group_ids:
            for attribute in group.attribute_ids:
                magento_attribute = None
                #TODO maybe adding a get_bind function can be better
                for bind in attribute.magento_bind_ids:
                    if bind.backend_id.id == self.backend_record.id:
                        magento_attribute = bind

                if not magento_attribute:
                    continue

                if attribute.ttype == 'many2one':
                    option = record[attribute.name]
                    if option:
                        result[magento_attribute.attribute_code] = \
                            option_binder.to_backend(option.id, wrap=True)
                    else:
                        result[magento_attribute.attribute_code] = False
                elif attribute.ttype == 'many2many':
                    options = record[attribute.name]
                    if options:
                        result[magento_attribute.attribute_code] = \
                            [option_binder.to_backend(option.id, wrap=True) for option in options]
                    else:
                        result[magento_attribute.attribute_code] = False
                else:
                    #TODO add support of lang
                    result[magento_attribute.attribute_code] = record[attribute.name]
        return result
