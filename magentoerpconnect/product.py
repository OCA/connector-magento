# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier, David Beal
#    Copyright 2013 Camptocamp SA
#    Copyright 2013 Akretion
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

import logging
import urllib2
import base64
from operator import itemgetter
from openerp.osv import orm, fields
from openerp.addons.connector.queue.job import job
from openerp.addons.connector.event import on_record_create, on_record_write
from openerp.addons.connector.unit.synchronizer import (ImportSynchronizer,
                                                        ExportSynchronizer
                                                        )
from openerp.addons.connector.exception import (MappingError,
                                                InvalidDataError)
from openerp.addons.connector.unit.mapper import (mapping,
                                                  ImportMapper
                                                  )
from .unit.backend_adapter import GenericAdapter
from .unit.import_synchronizer import (DelayedBatchImport,
                                       MagentoImportSynchronizer,
                                       TranslationImporter,
                                       AddCheckpoint,
                                       )
from .connector import get_environment
from .consumer import magento_consumer
from .backend import magento

_logger = logging.getLogger(__name__)


class magento_product_product(orm.Model):
    _name = 'magento.product.product'
    _inherit = 'magento.binding'
    _inherits = {'product.product': 'openerp_id'}
    _description = 'Magento Product'

    def product_type_get(self, cr, uid, context=None):
        return [
            ('simple', 'Simple Product'),
            # XXX activate when supported
            # ('grouped', 'Grouped Product'),
            # ('configurable', 'Configurable Product'),
            # ('virtual', 'Virtual Product'),
            # ('bundle', 'Bundle Product'),
            # ('downloadable', 'Downloadable Product'),
        ]

    def _product_type_get(self, cr, uid, context=None):
        return self.product_type_get(cr, uid, context=context)

    _columns = {
        'openerp_id': fields.many2one('product.product',
                                      string='Product',
                                      required=True,
                                      ondelete='restrict'),
        # XXX website_ids can be computed from categories
        'website_ids': fields.many2many('magento.website',
                                        string='Websites',
                                        readonly=True),
        'created_at': fields.date('Created At (on Magento)'),
        'updated_at': fields.date('Updated At (on Magento)'),
        'product_type': fields.selection(_product_type_get,
                                         'Magento Product Type',
                                         required=True),
        'manage_stock': fields.selection(
            [('use_default', 'Use Default Config'),
             ('no', 'Do Not Manage Stock'),
             ('yes', 'Manage Stock')],
            string='Manage Stock Level',
            required=True),
        'backorders': fields.selection(
            [('use_default', 'Use Default Config'),
             ('no', 'No Sell'),
             ('yes', 'Sell Quantity < 0'),
             ('yes-and-notification', 'Sell Quantity < 0 and Use Customer Notification')],
            string='Manage Inventory Backorders',
            required=True),
        'magento_qty': fields.float('Computed Quantity',
                                    help="Last computed quantity to send "
                                         "on Magento."),
        }

    _defaults = {
        'product_type': 'simple',
        'manage_stock': 'use_default',
        'backorders': 'use_default',
        }

    _sql_constraints = [
        ('magento_uniq', 'unique(backend_id, magento_id)',
         "A product with the same ID on Magento already exists")
    ]

    def recompute_magento_qty(self, cr, uid, ids, context=None):
        if not hasattr(ids, '__iter__'):
            ids = [ids]

        for product in self.browse(cr, uid, ids, context=context):
            new_qty = self._magento_qty(cr, uid, product, context=context)
            if new_qty != product.magento_qty:
                self.write(cr, uid, product.id,
                           {'magento_qty': new_qty},
                           context=context)
        return True

    def _magento_qty(self, cr, uid, product, context=None):
        if context is None:
            context = {}
        backend = product.backend_id
        stock = backend.warehouse_id.lot_stock_id

        if backend.product_stock_field_id:
            stock_field = backend.product_stock_field_id.name
        else:
            stock_field = 'virtual_available'

        location_ctx = context.copy()
        location_ctx['location'] = stock.id
        product_stk = self.read(cr, uid, product.id,
                                [stock_field],
                                context=location_ctx)
        return product_stk[stock_field]


class product_product(orm.Model):
    _inherit = 'product.product'

    _columns = {
        'magento_bind_ids': fields.one2many(
            'magento.product.product',
            'openerp_id',
            string='Magento Bindings',),
    }


@magento
class ProductProductAdapter(GenericAdapter):
    _model_name = 'magento.product.product'
    _magento_model = 'catalog_product'

    def search(self, filters=None, from_date=None):
        """ Search records according to some criterias
        and returns a list of ids

        :rtype: list
        """
        if filters is None:
            filters = {}
        if from_date is not None:
            filters['updated_at'] = {'from': from_date.strftime('%Y/%m/%d %H:%M:%S')}
        with self._magento_api() as api:
            # TODO add a search entry point on the Magento API
            return [int(row['product_id']) for row
                    in api.call('%s.list' % self._magento_model,
                                [filters] if filters else [{}])]

    def read(self, id, storeview_id=None, attributes=None):
        """ Returns the information of a record

        :rtype: dict
        """
        with self._magento_api() as api:
            return api.call('%s.info' % self._magento_model,
                            [id, storeview_id, attributes, 'id'])

    def get_images(self, id, storeview_id=None):
        with self._magento_api() as api:
            return api.call('product_media.list', [id, storeview_id, 'id'])

    def read_image(self, id, image_name, storeview_id=None):
        with self._magento_api() as api:
            return api.call('product_media.info', [id, image_name, storeview_id, 'id'])

    def update_inventory(self, id, data):
        with self._magento_api() as api:
            # product_stock.update is too slow
            return api.call('oerp_cataloginventory_stock_item.update',
                            [id, data])



@magento
class ProductBatchImport(DelayedBatchImport):
    """ Import the Magento Products.

    For every product category in the list, a delayed job is created.
    Import from a date
    """
    _model_name = ['magento.product.product']

    def run(self, filters=None):
        """ Run the synchronization """
        from_date = filters.pop('from_date', None)
        record_ids = self.backend_adapter.search(filters, from_date)
        _logger.info('search for magento products %s returned %s',
                     filters, record_ids)
        for record_id in record_ids:
            self._import_record(record_id)


@magento
class CatalogImageImporter(ImportSynchronizer):
    """ Import images for a record.

    Usually called from importers, in ``_after_import``.
    For instance from the products importer.
    """

    _model_name = ['magento.product.product',
                   ]

    def _get_images(self, storeview_id=None):
        return self.backend_adapter.get_images(self.magento_id, storeview_id)

    def _get_main_image_data(self, images):
        if not images:
            return {}
        # search if we have a base image defined
        image = next((img for img in images if 'base' in img['types']),
                     None)
        if image is None:
            # take the first image by priority
            images = sorted(images, key=itemgetter('position'))
            image = images[0]
        return image

    def _get_binary_image(self, image_data):
        url = image_data['url']
        binary = urllib2.urlopen(url)
        return binary.read()

    def run(self, magento_id, openerp_id):
        self.magento_id = magento_id
        images = self._get_images()
        main_image_data = self._get_main_image_data(images)
        if not main_image_data:
            return
        binary = self._get_binary_image(main_image_data)
        self.session.write(self.model._name,
                           openerp_id,
                           {'image': base64.b64encode(binary)})


@magento
class ProductImport(MagentoImportSynchronizer):
    _model_name = ['magento.product.product']

    def _import_dependencies(self):
        """ Import the dependencies for the record"""
        record = self.magento_record
        # import related categories
        binder = self.get_binder_for_model('magento.product.category')
        for mag_category_id in record['categories']:
            if binder.to_openerp(mag_category_id) is None:
                importer = self.get_connector_unit_for_model(
                    MagentoImportSynchronizer,
                    model='magento.product.category')
                importer.run(mag_category_id)

    def _validate_product_type(self, data):
        """ Check if the product type is in the selection (so we can
        prevent the `except_orm` and display a better error message).
        """
        sess = self.session
        product_type = data['product_type']
        cr, uid, context = sess.cr, sess.uid, sess.context
        product_obj = sess.pool['magento.product.product']
        types = product_obj.product_type_get(cr, uid, context=context)
        available_types = [typ[0] for typ in types]
        if product_type not in available_types:
            raise InvalidDataError("The product type '%s' is not "
                                   "yet supported in the connector." %
                                   product_type)

    def _validate_data(self, data):
        """ Check if the values to import are correct

        Pro-actively check before the ``_create`` or
        ``_update`` if some fields are missing or invalid

        Raise `InvalidDataError`
        """
        self._validate_product_type(data)

    def _create(self, data):
        openerp_binding_id = super(ProductImport, self)._create(data)
        checkpoint = self.get_connector_unit_for_model(AddCheckpoint)
        checkpoint.run(openerp_binding_id)
        return openerp_binding_id

    def _after_import(self, openerp_id):
        """ Hook called at the end of the import """
        translation_importer = self.get_connector_unit_for_model(
            TranslationImporter, self.model._name)
        translation_importer.run(self.magento_id, openerp_id)
        image_importer = self.get_connector_unit_for_model(
            CatalogImageImporter, self.model._name)
        image_importer.run(self.magento_id, openerp_id)


@magento
class ProductImportMapper(ImportMapper):
    _model_name = 'magento.product.product'
    #TODO :     categ, special_price => minimal_price
    direct = [('name', 'name'),
              ('description', 'description'),
              ('weight', 'weight'),
              ('price', 'list_price'),
              ('cost', 'standard_price'),
              ('short_description', 'description_sale'),
              ('sku', 'default_code'),
              ('type_id', 'product_type'),
              ('created_at', 'created_at'),
              ('updated_at', 'updated_at'),
              ]

    @mapping
    def type(self, record):
        if record['type_id'] == 'simple':
            return {'type': 'product'}
        return

    @mapping
    def website_ids(self, record):
        website_ids = []
        for mag_website_id in record['websites']:
            binder = self.get_binder_for_model('magento.website')
            website_id = binder.to_openerp(mag_website_id)
            website_ids.append(website_id)
        return {'website_ids': website_ids}

    @mapping
    def categories(self, record):
        mag_categories = record['categories']
        binder = self.get_binder_for_model('magento.product.category')

        category_ids = []
        main_categ_id = None

        for mag_category_id in mag_categories:
            cat_id = binder.to_openerp(mag_category_id, unwrap=True)
            if cat_id is None:
                raise MappingError("The product category with "
                                   "magento id %s is not imported." %
                                   mag_category_id)

            category_ids.append(cat_id)

        if category_ids:
            main_categ_id = category_ids.pop(0)

        if main_categ_id is None:
            default_categ = self.backend_record.default_category_id
            if default_categ:
                main_categ_id = default_categ.id

        result = {'categ_ids': [(6, 0, category_ids)]}
        if main_categ_id:  # OpenERP assign 'All Products' if not specified
            result['categ_id'] = main_categ_id
        return result

    @mapping
    def magento_id(self, record):
        return {'magento_id': record['product_id']}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}


@magento
class ProductInventoryExport(ExportSynchronizer):
    _model_name = ['magento.product.product']

    _map_backorders = {'use_default': 0,
                       'no': 0,
                       'yes': 1,
                       'yes-and-notification': 2,
                       }

    def _get_data(self, product, fields):
        result = {}
        if 'magento_qty' in fields:
            result.update({
                'qty': product.magento_qty,
                # put the stock availability to "out of stock"
                'is_in_stock': int(product.magento_qty > 0)
            })
        if 'manage_stock' in fields:
            manage = product.manage_stock
            result.update({
                'manage_stock': int(manage == 'yes'),
                'use_config_manage_stock': int(manage == 'use_default'),
            })
        if 'backorders' in fields:
            backorders = product.backorders
            result.update({
                'backorders': self._map_backorders[backorders],
                'use_config_backorders': int(backorders == 'use_default'),
            })
        return result

    def run(self, openerp_id, fields):
        """ Export the product inventory to Magento """
        product = self.session.browse(self.model._name, openerp_id)
        binder = self.get_binder_for_model()
        magento_id = binder.to_backend(product.id)
        data = self._get_data(product, fields)
        self.backend_adapter.update_inventory(magento_id, data)


# fields which should not trigger an export of the products
# but an export of their inventory
INVENTORY_FIELDS = ('manage_stock',
                    'backorders',
                    'magento_qty',
                    )


@on_record_write(model_names='magento.product.product')
@magento_consumer
def magento_product_modified(session, model_name, record_id, fields=None):
    if session.context.get('connector_no_export'):
        return
    inventory_fields = list(set(fields).intersection(INVENTORY_FIELDS))
    if inventory_fields:
        export_product_inventory.delay(session, model_name,
                                       record_id, fields=inventory_fields,
                                       priority=20)


@job
def export_product_inventory(session, model_name, record_id, fields=None):
    """ Export the inventory configuration and quantity of a product. """
    product = session.browse(model_name, record_id)
    backend_id = product.backend_id.id
    env = get_environment(session, model_name, backend_id)
    inventory_exporter = env.get_connector_unit(ProductInventoryExport)
    return inventory_exporter.run(record_id, fields)
