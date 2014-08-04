# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright 2013
#    Author: David Béal - Akretion
#            Sébastien Beau - Akretion
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

import mimetypes

from openerp.osv import fields, orm
from openerp.addons.connector.unit.mapper import (mapping,
                                                  ExportMapper)
from openerp.addons.magentoerpconnect.unit.binder import MagentoModelBinder
from openerp.addons.magentoerpconnect.unit.delete_synchronizer import (
    MagentoDeleteSynchronizer)
from openerp.addons.magentoerpconnect.unit.export_synchronizer import (
    MagentoExporter)
from openerp.addons.magentoerpconnect.backend import magento
from openerp.addons.magentoerpconnect.unit.backend_adapter import GenericAdapter


MAGENTO_HELP = "This field is a technical / configuration field for " \
               "the attribute on Magento. \nPlease refer to the Magento " \
               "documentation for details. "


@magento(replacing=MagentoModelBinder)
class MagentoImageBinder(MagentoModelBinder):
    _model_name = [
        'magento.product.image',
    ]


class ProductImage(orm.Model):
    _inherit = 'product.image'

    _columns = {
        'magento_bind_ids': fields.one2many(
            'magento.product.image',
            'openerp_id',
            string='Magento bindings',),
    }

    #Automatically create the magento binding for the image created
    def create(self, cr, uid, vals, context=None):
        image_id = super(ProductImage, self).\
            create(cr, uid, vals, context=None)
        mag_image_obj = self.pool['magento.product.image']
        image = self.browse(cr, uid, image_id, context=context)
        for binding in image.product_id.magento_bind_ids:
            if binding.backend_id.auto_bind_image:
                mag_image_obj.create(cr, uid, {
                    'openerp_id': image_id,
                    'backend_id': binding.backend_id.id,
                    }, context=context)
        return image_id


class MagentoProductImage(orm.Model):
    _name = 'magento.product.image'
    _description = "Magento product image"
    _inherit = 'magento.binding'
    _inherits = {'product.image': 'openerp_id'}

    _columns = {
        'openerp_id': fields.many2one(
            'product.image',
            required=True,
            ondelete="cascade",
            string='Image'),
    }

    _sql_constraints = [
        ('magento_uniq', 'unique(backend_id, magento_id)',
         "An image with the same ID on Magento already exists")
    ]

@magento
class ProductImageDeleteSynchronizer(MagentoDeleteSynchronizer):
    _model_name = ['magento.product.image']

@magento
class ProductImageExporter(MagentoExporter):
    _model_name = ['magento.product.image']

    def _should_import(self):
        "Images in magento doesn't retrieve infos on dates"
        return False

@magento
class ProductImageExportMapper(ExportMapper):
    _model_name = 'magento.product.image'

    direct = [
            ('name', 'label'),
            ('sequence', 'position'),
        ]

    @mapping
    def product(self, record):
        binder = self.get_binder_for_model('magento.product.product')
        external_product_id = binder.to_backend(
            record.openerp_id.product_id.id, True)
        return {'product': str(external_product_id)}

    @mapping
    def identifierType(self, record):
        return {'identifierType': 'ID'}

    @mapping
    def types(self, record):
        product_obj = self.session.pool['product.product']
        cr = self.session.cr
        uid = self.session.uid
        main_image_id = product_obj._get_main_image_id(
            cr, uid, record.product_id.id)
        if record.openerp_id.id == main_image_id:
            return {'types': ['image', 'small_image', 'thumbnail']}
        else:
            return {'types': []}

    @mapping
    def file(self, record):
        ctx = record._context.copy()
        ctx['bin_base64'] = True
        record = record.browse(context=ctx)[0]
        return {
            'file': {
            'mime': mimetypes.guess_type(record.file_name)[0],
            'name': record.name,
            'content': record.image,
            }
        }


@magento
class ProductImageAdapter(GenericAdapter):
    _model_name = 'magento.product.image'
    _magento_model = 'catalog_product_attribute_media'

    def create(self, data, storeview_id=None):
        return self._call('%s.create' % self._magento_model,
                          [data.pop('product'), data, storeview_id])

    def write(self, id, data):
        """ Update records on the external system
            changes with GenericAdapter : prevent 'int(id)' """
        return self._call('%s.update' % self._magento_model,
                          [data.pop('product'), id, data])

    def delete(self, id):
        """ Delete a record on the external system """
        image_id, external_product_id = id
        return self._call('%s.remove' % self._magento_model,
                          [external_product_id, image_id])
