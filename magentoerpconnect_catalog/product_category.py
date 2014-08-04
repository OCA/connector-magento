# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright 2013
#    Author: Guewen Baconnier - Camptocamp SA
#            Augustin Cisterne-Kaasv - Elico-corp
#            David Béal - Akretion
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
                                                  #changed_by,
                                                  ExportMapper)
from openerp.addons.magentoerpconnect.unit.delete_synchronizer import (
        MagentoDeleteSynchronizer)
from openerp.addons.magentoerpconnect.unit.export_synchronizer import (
        MagentoTranslationExporter)
from openerp.addons.magentoerpconnect.backend import magento
from openerp.addons.magentoerpconnect.product_category import (
    ProductCategoryImageAdapter,
    ProductCategoryAdapter,
    )
from openerp.addons.connector.unit.synchronizer import ExportSynchronizer
from openerp.addons.connector.event import on_record_write, on_record_create
from openerp.addons.connector.queue.job import job, related_action
from openerp.addons.magentoerpconnect.related_action import unwrap_binding
from openerp.addons.magentoerpconnect.connector import get_environment


class MagentoProductCategory(orm.Model):
    _inherit = 'magento.product.category'
    MAGENTO_HELP = "This field is a technical / configuration field for " \
                   "the category on Magento. \nPlease refer to the Magento " \
                   "documentation for details. "

    def get_custom_design(self, cr, uid, context=None):
        return [
            ('base/default', 'base default'),
            ('default/modern', 'default modern'),
            ('default/iphone', 'default iphone'),
            ('default/default', 'default default'),
            ('default/blank', 'default blank'),
            ]

    def _get_custom_design(self, cr, uid, context=None):
        return self.get_custom_design(cr, uid, context=context)

    def get_page_layout(self, cr, uid, context=None):
        return [
            ('empty', 'Empty'),
            ('one_column', '1 colmun'),
            ('two_columns_left', '2 columns with left bar'),
            ('two_columns_right', '2 columns with right bar'),
            ('three_columns', '3 columns'),
            ]

    def _get_page_layout(self, cr, uid, context=None):
        return self.get_page_layout(cr, uid, context=context)

    _columns = {
        #==== General Information ====
        'meta_title': fields.char('Title (Meta)', size=75, help=MAGENTO_HELP),
        'meta_keywords': fields.text('Meta Keywords', help=MAGENTO_HELP),
        'meta_description': fields.text('Meta Description', help=MAGENTO_HELP),
        'url_key': fields.char('URL-key', size=100, readonly="True"),
        #==== Display Settings ====
        'display_mode': fields.selection([
                    ('PRODUCTS', 'Products Only'),
                    ('PAGE', 'Static Block Only'),
                    ('PRODUCTS_AND_PAGE', 'Static Block & Products')],
            'Display Mode', required=True, help=MAGENTO_HELP),
        'is_anchor': fields.boolean('Anchor?', help=MAGENTO_HELP),
        'use_default_available_sort_by': fields.boolean(
            'Default Config For Available Sort By', help=MAGENTO_HELP),

        #TODO use custom attribut for category

        #'available_sort_by': fields.sparse(
        #    type='many2many',
        #    relation='magerp.product_category_attribute_options',
        #    string='Available Product Listing (Sort By)',
        #    serialization_field='magerp_fields',
        #    domain="[('attribute_name', '=', 'sort_by'), ('value', '!=','None')]",
        #    help=MAGENTO_HELP),
        #filter_price_range landing_page ?????????????
        'default_sort_by': fields.selection([
                    ('_', 'Config settings'), #?????????????
                    ('position', 'Best Value'),
                    ('name', 'Name'),
                    ('price', 'Price')],
            'Default sort by', required=True, help=MAGENTO_HELP),

        #==== Custom Design ====
        'custom_apply_to_products': fields.boolean(
            'Apply to products', help=MAGENTO_HELP),
        'custom_design': fields.selection(
            _get_custom_design,
            string='Custom design',
            help=MAGENTO_HELP),
        'custom_design_from': fields.date(
            'Active from', help=MAGENTO_HELP),
        'custom_design_to': fields.date(
            'Active to', help=MAGENTO_HELP),
        'custom_layout_update': fields.text(
            'Layout update', help=MAGENTO_HELP),
        'page_layout': fields.selection(
            _get_page_layout,
            'Page layout', help=MAGENTO_HELP),
    }

    _defaults = {
        'display_mode': 'PRODUCTS',
        'use_default_available_sort_by': True,
        'default_sort_by': '_',
        'is_anchor': True,
        'include_in_menu': True,
        }

    _sql_constraints = [
        ('magento_img_uniq', 'unique(backend_id, image)',
         "'Image file name' already exists : must be unique"),
        ('magento_thumb_uniq', 'unique(backend_id, thumbnail)',
         "'thumbnail name' already exists : must be unique"),
    ]


@magento
class ProductCategoryDeleteSynchronizer(MagentoDeleteSynchronizer):
    """ Product category deleter for Magento """
    _model_name = ['magento.product.category']

    @property
    def backend_adapter(self):
        get_unit = self.environment.get_connector_unit
        self._backend_adapter = get_unit(ProductCategoryAdapter)
        return self._backend_adapter


@magento
class ProductCategoryExporter(MagentoTranslationExporter):
    _model_name = ['magento.product.category']

    @property
    def backend_adapter(self):
        get_unit = self.environment.get_connector_unit
        self._backend_adapter = get_unit(ProductCategoryAdapter)
        return self._backend_adapter

    def _export_dependencies(self):
        """Export parent of the category"""
        record = self.binding_record
        if record.magento_parent_id:
            self._export_dependency(record.magento_parent_id,
                                    'magento.product.category',
                                    exporter_class=ProductCategoryExporter)
        elif record.parent_id:
            self._export_dependency(record.parent_id,
                                    'magento.product.category',
                                    exporter_class=ProductCategoryExporter)


@magento
class ProductCategoryExportMapper(ExportMapper):
    _model_name = 'magento.product.category'

    direct = [('description', 'description'),
              #change that to mapping top level category has no name
              ('name', 'name'),
              ('meta_title', 'meta_title'),
              ('meta_keywords', 'meta_keywords'),
              ('meta_description', 'meta_description'),
              ('display_mode', 'display_mode'),
              ('is_anchor', 'is_anchor'),
              ('use_default_available_sort_by', 'use_default_available_sort_by'),
              ('custom_design', 'custom_design'),
              ('custom_design_from', 'custom_design_from'),
              ('custom_design_to', 'custom_design_to'),
              ('custom_layout_update', 'custom_layout_update'),
              ('page_layout', 'page_layout'),
              ('image_name', 'image'),
              ('image_name', 'thumbnail'),
             ]

    @mapping
    def sort(self, record):
        return {'default_sort_by':'price', 'available_sort_by': 'price'}

    @mapping
    def parent(self, record):
        """ Magento root category's Id equals 1 """
        if not record.magento_parent_id:
            openerp_parent = record.parent_id
            binder = self.get_binder_for_model('magento.product.category')
            parent_id = binder.to_backend(openerp_parent.id, wrap=True)
        else:
            parent_id = record.magento_parent_id.magento_id
        if not parent_id:
            parent_id = 1
        return {'parent_id':parent_id}

    @mapping
    def active(self, record):
        is_active = record['is_active']
        if not is_active:
            is_active = 0
        return {'is_active':is_active}

    @mapping
    def menu(self, record):
        include_in_menu = record['include_in_menu']
        if not include_in_menu:
            include_in_menu = 0
        return {'include_in_menu':include_in_menu}


# TODO add mapping for default_sort_by and available_sort_by
#@magento(replacing=product_category.ProductCategoryImportMapper)
#class ProductCategoryImportMapper(product_category.ProductCategoryImportMapper):
#    _model_name = 'magento.product.category'
#    direct = product_category.ProductCategoryImportMapper.direct + []


@magento
class ProductCategoryImageExporter(ExportSynchronizer):
    _model_name = ['magento.product.category']

    @property
    def backend_adapter(self):
        get_unit = self.environment.get_connector_unit
        self._backend_adapter = get_unit(ProductCategoryImageAdapter)
        return self._backend_adapter

    def _prepare_create(self, categ, image_field):
        if image_field == 'image' and categ.image and categ.image_name:
            return [categ.image_name, categ.image]
        else:
            return None

    def run(self, binding_id, image_field):
        cr = self.session.cr
        uid = self.session.uid
        ctx = self.session.context.copy()
        ctx['bin_base64_image'] = True
        categ = self.session.pool[self.model._name].\
            browse(cr, uid, binding_id, context=ctx)
        args = self._prepare_create(categ, image_field)
        if args:
            self.backend_adapter.create(*args)


@on_record_write(model_names='product.category')
def product_category_modified(session, model_name, record_id, vals):
    if session.context.get('connector_no_export'):
        return
    image_fields = list(set(vals).intersection(['image', 'image_medium']))
    if image_fields:
        categ_obj = session.pool['product.category']
        record = categ_obj.browse(session.cr, session.uid,
                              record_id, context=session.context)
        for binding in record.magento_bind_ids:
            export_product_category_image.delay(
                session, binding._model._name, binding.id, 'image',
                priority=50)


@on_record_create(model_names='magento.product.category')
def magento_product_category_created(session, model_name, record_id, vals):
    if session.context.get('connector_no_export'):
        return
    export_product_category_image.delay(
        session, 'magento.product.category', record_id, 'image',
        priority=50)


@job
@related_action(action=unwrap_binding)
def export_product_category_image(session, model_name, record_id, image_field):
    """ Export the image of a product category. """
    categ = session.browse(model_name, record_id)
    backend_id = categ.backend_id.id
    env = get_environment(session, model_name, backend_id)
    categ_image_exporter = env.get_connector_unit(ProductCategoryImageExporter)
    return categ_image_exporter.run(record_id, image_field)
