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

from openerp.osv import fields, orm, osv
from openerp.addons.connector.queue.job import job
from openerp.addons.connector.unit.mapper import (mapping,
                                                  changed_by,
                                                  ExportMapper)
from openerp.addons.magentoerpconnect.unit.delete_synchronizer import (
        MagentoDeleteSynchronizer)
from openerp.addons.magentoerpconnect.unit.export_synchronizer import (
        MagentoTranslationExporter)
from openerp.addons.magentoerpconnect.backend import magento
from openerp.addons.magentoerpconnect.product import ProductProductAdapter
from openerp.addons.connector.exception import MappingError
from openerp.addons.magentoerpconnect.unit.export_synchronizer import (
    export_record
)


class MagentoProductProduct(orm.Model):
    _inherit='magento.product.product'

    #Automatically create the magento binding for each image
    def create(self, cr, uid, vals, context=None):
        mag_image_obj = self.pool['magento.product.image']
        mag_product_id = super(MagentoProductProduct, self).\
            create(cr, uid, vals, context=None)
        mag_product = self.browse(cr, uid, mag_product_id, context=context)
        if mag_product.backend_id.auto_bind_image:
            for image in mag_product.image_ids:
                mag_image_obj.create(cr, uid, {
                    'openerp_id': image.id,
                    'backend_id': mag_product.backend_id.id,
                    }, context=context)
        return mag_product_id


@magento
class ProductProductDeleteSynchronizer(MagentoDeleteSynchronizer):
    """ Partner deleter for Magento """
    _model_name = ['magento.product.product']


@magento
class ProductProductExport(MagentoTranslationExporter):
    _model_name = ['magento.product.product']

    def _export_dependencies(self):
        """ Export the dependencies for the product"""
        #TODO add export of category
        attribute_binder = self.get_binder_for_model('magento.product.attribute')
        option_binder = self.get_binder_for_model('magento.attribute.option')
        record = self.binding_record
        for group in record.attribute_group_ids:
            for attribute in group.attribute_ids:
                attribute_ext_id = attribute_binder.to_backend(attribute.attribute_id.id, wrap=True)
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
                                                    self.session.cr, self.session.uid,{
                                                    'backend_id': self.backend_record.id,
                                                    'openerp_id': option.id,
                                                    'name': option.name,
                                                    }, context=ctx)
                            export_record(self.session, 'magento.attribute.option', binding_id)


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
                'price': record.list_price,
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
        attribute_binder = self.get_binder_for_model('magento.product.attribute')
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
                        continue
                elif attribute.ttype == 'many2many':
                    options = record[attribute.name]
                    if options:
                        result[magento_attribute.attribute_code] = \
                            [option_binder.to_backend(option.id, wrap=True) for option in options]
                    else:
                        continue
                else:
                    #TODO add support of lang
                    result[magento_attribute.attribute_code] = record[attribute.name]
        return result
