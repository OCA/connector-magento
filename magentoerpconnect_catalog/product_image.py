# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright 2013
#    Author: Guewen Baconnier - Camptocamp
#            David Béal - Akretion
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
#from openerp.tools.translate import _
#from openerp.osv.osv import except_osv
from openerp.addons.connector.unit.mapper import (mapping,
                                                  ExportMapper)
from openerp.addons.magentoerpconnect.unit.delete_synchronizer import (
        MagentoDeleteSynchronizer)
from openerp.addons.magentoerpconnect.unit.export_synchronizer import (
        MagentoExporter)
from openerp.addons.magentoerpconnect.backend import magento
from openerp.addons.magentoerpconnect.unit.backend_adapter import GenericAdapter


MAGENTO_HELP = "This field is a technical / configuration field for " \
               "the attribute on Magento. \nPlease refer to the Magento " \
               "documentation for details. "


class MagentoProductProduct(orm.Model):
    _inherit = 'magento.product.product'

    def _get_images(self, cr, uid, ids, field_names, arg, context=None):
        res={}
        for prd in self.browse(cr, uid, ids, context=context):
            img_ids = self.pool['magento.product.image'].search(cr, uid, [
                        ('product_id', '=', prd.openerp_id.id),
                        ('backend_id', '=', prd.backend_id.id),
                                                        ], context=context)
            res[prd.id] = img_ids
        return res

    def copy(self, cr, uid, id, default=None, context=None):
        #take care about duplicate on one2many and function fields
        #https://bugs.launchpad.net/openobject-server/+bug/705364
        if default is None:
            default = {}
        default['magento_product_image_ids'] = None
        return super(MagentoProductProduct, self).copy(cr, uid, id,
                                                       default=default,
                                                       context=context)
    _columns = {
        'magento_product_image_ids': fields.function(
            _get_images,
            type='one2many',
            relation='magento.product.image',
            string='Magento product images'),
        'magento_product_storeview_ids': fields.one2many(
            'magento.product.storeview',
            'magento_product_id',
            string='Magento storeview',),
    }

    def open_images(self, cr, uid, ids, context=None):
        view_id = self.pool['ir.model.data'].get_object_reference(
            cr, uid, 'magentoerpconnect_catalog',
            'magento_product_img_form_view')[1]
        return {
            'name': 'Product images',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'res_model': self._name,
            'context': context,
            'type': 'ir.actions.act_window',
            'res_id': ids and ids[0] or False,
        }


class ProductImage(orm.Model):
    _inherit = 'product.image'

    _columns = {
        'magento_bind_ids': fields.one2many(
            'magento.product.image',
            'openerp_id',
            string='Magento bindings',),
    }


class MagentoProductImage(orm.Model):
    _name = 'magento.product.image'
    _description = "Magento product image"
    _inherit = 'magento.binding'
    _inherits = {'product.image': 'openerp_id'}

    _columns = {
        'openerp_id' : fields.many2one(
            'product.image',
            required=True,
            ondelete="cascade",
            string='Image'),
    }

    def _get_backend(self, cr, uid, context=None):
        backend_id = False
        backend_m = self.pool['magento.backend']
        back_ids = backend_m.search(cr, uid, [], context=context)
        if back_ids:
            backend_id = backend_m.browse(cr, uid, back_ids,
                                          context=context)[0].id
        return backend_id

    _defaults = {
        'backend_id': _get_backend,
    }

    _sql_constraints = [
        ('magento_uniq', 'unique(backend_id, magento_id)',
         "An image with the same ID on Magento already exists")
    ]

@magento
class ProductImageDeleteSynchronizer(MagentoDeleteSynchronizer):
    _model_name = ['magento.product.image']


@magento
class ProductImageExport(MagentoExporter):
    _model_name = ['magento.product.image']

    def _should_import(self):
        "Images in magento doesn't retrieve infos on dates"
        return False


@magento
class ProductImageExportMapper(ExportMapper):
    _model_name = 'magento.product.image'

    direct = [
            ('label', 'label'),
            ('sequence', 'position'),
        ]

    @mapping
    def product(self, record):
        binder = self.get_binder_for_model('magento.product.product')
        external_product_id = binder.to_backend(record.openerp_id.product_id.id, True)
        return {'product': str(external_product_id)}
    #@mapping
    #def other(self, record):
    #    return {
    #        'exclude': int(record.exclude),
    #        }

    @mapping
    def identifierType(self, record):
        return {'identifierType': 'ID'}

    @mapping
    def types(self, record):
        return {'types': ['image', 'small_image', 'thumbnail']}
        import pdb;pdb.set_trace()
    #    return {'types':
    #            [x for x in ['image', 'small_image', 'thumbnail'] if record[x]]
    #           }

    @mapping
    def file(self, record):
        return {'file': {
                'mime': mimetypes.guess_type(record.name + record.extension)[0],
                'mime': 'image/jpeg',
                'name': record.label,
                'content': self.session.pool['image.image']
                    .get_image(self.session.cr, self.session.uid,
                        record.openerp_id.image_id.id,
                        context=self.session.context),
                }
            }


@magento
class ProductImageAdapter(GenericAdapter):
    _model_name = 'magento.product.image'
    _magento_model = 'catalog_product_attribute_media'

    def create(self, data, storeview_id=None):
        #import pdb;pdb.set_trace()
        print data
        return self._call('%s.create'% self._magento_model,
            [data.pop('product'), data, storeview_id])

    def write(self, id, data):
        """ Update records on the external system
            changes with GenericAdapter : prevent 'int(id)' """
        return self._call('%s.update' % self._magento_model,
                          [data.pop('product'), id, data])

    def delete(self, id):
        """ Delete a record on the external system """
        image_id, external_product_id  = id
        return self._call('%s.remove' % self._magento_model,
                          [external_product_id, image_id])


class MagentoProductStoreview(orm.Model):
    _name = 'magento.product.storeview'
    _description = "Magento product storeview"
    _inherits = {'magento.product.product': 'magento_product_id'}

    _columns = {
        'magento_product_id' : fields.many2one(
            'magento.product.product',
            required=True,
            ondelete="cascade",
            string='Image'),
        'storeview_id' : fields.many2one(
            'magento.storeview',
            required=True,
            string='Storeview'),
        'image': fields.many2one(
            'magento.product.image',
            'Base image',
            help=MAGENTO_HELP),
        'small_image': fields.many2one(
            'magento.product.image',
            'Small image',
            help=MAGENTO_HELP),
        'thumbnail': fields.many2one(
            'magento.product.image',
            'Thumbnail',
            domain="[('backend_id', '=', 'backend_id')]",
            help=MAGENTO_HELP),
        'exclude_ids': fields.many2many(
            'magento.product.image', 'product_id',
            string='Exclude',
            help=MAGENTO_HELP),
    }
#

@magento
class ProductStoreviewExport(MagentoExporter):
    _model_name = ['magento.product.storeview']

#    TODO
#    def _export_dependencies(self):


    def _should_import(self):
        "Images in magento doesn't retrieve infos on dates"
        return False
    #
    #def _run(self, fields=None):
    #    """ Flow of the synchronization, implemented in inherited classes"""
    #    assert self.binding_id
    #    assert self.binding_record
    #
    #
    #    if not self.magento_id:
    #        fields = None  # should be created with all the fields
    #
    #    if self._has_to_skip():
    #        return
    #
    #     export the missing linked resources
    #    self._export_dependencies()
    #
    #    self._map_data(fields=fields)
    #
    #    if self.magento_id:
    #        record = self.mapper.data
    #        if not record:
    #            return _('Nothing to export.')
    #         special check on data before export
    #        self._validate_data(record)
    #        self._update(record)
    #    else:
    #        record = self.mapper.data_for_create
    #        if not record:
    #            return _('Nothing to export.')
    #         special check on data before export
    #        self._validate_data(record)
    #        self.magento_id = self._create(record)
    #    return _('Record exported with ID %s on Magento.') % self.magento_id


@magento
class ProductStoreviewExportMapper(ExportMapper):
    _model_name = 'magento.product.storeview'

    direct = [
            ('label', 'label'),
            ('sequence', 'position'),
        ]

    @mapping
    def product(self, record):
        return {'product': ''}


#
#@magento
#class ProductStoreviewAdapter(GenericAdapter):
#    _model_name = 'magento.product.storeview'
#
#    def update_image(self, product_id, data, storeview_id=None):
#        #data = {'small', image_id, 'medium':image_id,...}
#
#        return self._call('catalog_product_attribute_media.update',
#            [product_id, image_id, data, storeview_id])
#



#
#@job
#def export_record(session, model_name, binding_id, fields=None):
#    """ Export a record on Magento """
#    record = session.browse(model_name, binding_id)
#    env = get_environment(session, model_name, record.backend_id.id)
#    exporter = env.get_connector_unit(MagentoExporter)
#    return exporter.run(binding_id, fields=fields)