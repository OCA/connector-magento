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
import xmlrpclib
import sys
from collections import defaultdict
from openerp.osv import orm, fields
from openerp.tools.translate import _
from openerp.addons.connector.queue.job import job, related_action
from openerp.addons.connector.event import on_record_write
from openerp.addons.connector.unit.synchronizer import (ImportSynchronizer,
                                                        ExportSynchronizer
                                                        )
from openerp.addons.connector.exception import (MappingError,
                                                InvalidDataError,
                                                IDMissingInBackend
                                                )
from openerp.addons.connector.unit.mapper import (mapping,
                                                  ImportMapper,
                                                  )
from .unit.backend_adapter import (GenericAdapter,
                                   MAGENTO_DATETIME_FORMAT,
                                   )
from .unit.mapper import normalize_datetime
from .unit.import_synchronizer import (DelayedBatchImport,
                                       MagentoImportSynchronizer,
                                       TranslationImporter,
                                       AddCheckpoint,
                                       )
from .connector import get_environment
from .backend import magento
from .related_action import unwrap_binding

_logger = logging.getLogger(__name__)


def chunks(items, length):
    for index in xrange(0, len(items), length):
        yield items[index:index + length]


class magento_product_product(orm.Model):
    _name = 'magento.product.product'
    _inherit = 'magento.binding'
    _inherits = {'product.product': 'openerp_id'}
    _description = 'Magento Product'

    def product_type_get(self, cr, uid, context=None):
        return [
            ('simple', 'Simple Product'),
            ('configurable', 'Configurable Product'),
            # XXX activate when supported
            # ('grouped', 'Grouped Product'),
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
             ('yes-and-notification', 'Sell Quantity < 0 and '
                                      'Use Customer Notification')],
            string='Manage Inventory Backorders',
            required=True),
        'magento_qty': fields.float('Computed Quantity',
                                    help="Last computed quantity to send "
                                         "on Magento."),
        'no_stock_sync': fields.boolean(
            'No Stock Synchronization',
            required=False,
            help="Check this to exclude the product "
                 "from stock synchronizations."),
        }

    _defaults = {
        'product_type': 'simple',
        'manage_stock': 'use_default',
        'backorders': 'use_default',
        'no_stock_sync': False,
        }

    _sql_constraints = [
        ('magento_uniq', 'unique(backend_id, magento_id)',
         "A product with the same ID on Magento already exists")
    ]

    RECOMPUTE_QTY_STEP = 1000  # products at a time

    def recompute_magento_qty(self, cr, uid, ids, context=None):
        """ Check if the quantity in the stock location configured
        on the backend has changed since the last export.

        If it has changed, write the updated quantity on `magento_qty`.
        The write on `magento_qty` will trigger an `on_record_write`
        event that will create an export job.

        It groups the products by backend to avoid to read the backend
        informations for each product.
        """
        if not hasattr(ids, '__iter__'):
            ids = [ids]

        # group products by backend
        backends = defaultdict(list)
        for product in self.read(cr, uid, ids, ['backend_id', 'magento_qty'],
                                 context=context):
            backends[product['backend_id'][0]].append(product)

        for backend_id, products in backends.iteritems():
            backend_obj = self.pool['magento.backend']
            backend = backend_obj.browse(cr, uid, backend_id, context=context)
            self._recompute_magento_qty_backend(cr, uid, backend, products,
                                                context=context)
        return True

    def _recompute_magento_qty_backend(self, cr, uid, backend, products,
                                       read_fields=None, context=None):
        """ Recompute the products quantity for one backend.

        If field names are passed in ``read_fields`` (as a list), they
        will be read in the product that is used in
        :meth:`~._magento_qty`.

        """
        if context is None:
            context = {}

        if backend.product_stock_field_id:
            stock_field = backend.product_stock_field_id.name
        else:
            stock_field = 'virtual_available'

        location = backend.warehouse_id.lot_stock_id
        location_ctx = context.copy()
        location_ctx['location'] = location.id

        product_fields = ['magento_qty', stock_field]
        if read_fields:
            product_fields += read_fields

        product_ids = [product['id'] for product in products]
        for chunk_ids in chunks(product_ids, self.RECOMPUTE_QTY_STEP):
            for product in self.read(cr, uid, chunk_ids, product_fields,
                                     context=location_ctx):
                new_qty = self._magento_qty(cr, uid, product,
                                            backend,
                                            location,
                                            stock_field,
                                            context=location_ctx)
                if new_qty != product['magento_qty']:
                    self.write(cr, uid, product['id'],
                               {'magento_qty': new_qty},
                               context=context)

    def _magento_qty(self, cr, uid, product, backend, location,
                     stock_field, context=None):
        """ Return the current quantity for one product.

        Can be inherited to change the way the quantity is computed,
        according to a backend / location.

        If you need to read additional fields on the product, see the
        ``read_fields`` argument of :meth:`~._recompute_magento_qty_backend`

        """
        return product[stock_field]


class product_product(orm.Model):
    _inherit = 'product.product'

    _columns = {
        'magento_bind_ids': fields.one2many(
            'magento.product.product',
            'openerp_id',
            string='Magento Bindings',),
    }

    def copy_data(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default['magento_bind_ids'] = False
        return super(product_product, self).copy_data(cr, uid, id,
                                                      default=default,
                                                      context=context)


@magento
class ProductProductAdapter(GenericAdapter):
    _model_name = 'magento.product.product'
    _magento_model = 'catalog_product'
    _admin_path = '/{model}/edit/id/{id}'

    def _call(self, method, arguments):
        try:
            return super(ProductProductAdapter, self)._call(method, arguments)
        except xmlrpclib.Fault as err:
            # this is the error in the Magento API
            # when the product does not exist
            if err.faultCode == 101:
                raise IDMissingInBackend
            else:
                raise

    def search(self, filters=None, from_date=None, to_date=None):
        """ Search records according to some criteria
        and returns a list of ids

        :rtype: list
        """
        if filters is None:
            filters = {}
        dt_fmt = MAGENTO_DATETIME_FORMAT
        if from_date is not None:
            filters.setdefault('updated_at', {})
            filters['updated_at']['from'] = from_date.strftime(dt_fmt)
        if to_date is not None:
            filters.setdefault('updated_at', {})
            filters['updated_at']['to'] = to_date.strftime(dt_fmt)
        # TODO add a search entry point on the Magento API
        return [int(row['product_id']) for row
                in self._call('%s.list' % self._magento_model,
                              [filters] if filters else [{}])]

    def read(self, id, storeview_id=None, attributes=None):
        """ Returns the information of a record

        :rtype: dict
        """
        return self._call('ol_catalog_product.info',
                          [int(id), storeview_id, attributes, 'id'])

    def write(self, id, data, storeview_id=None):
        """ Update records on the external system """
        # XXX actually only ol_catalog_product.update works
        # the PHP connector maybe breaks the catalog_product.update
        return self._call('ol_catalog_product.update',
                          [int(id), data, storeview_id, 'id'])

    def get_images(self, id, storeview_id=None):
        return self._call('product_media.list', [int(id), storeview_id, 'id'])

    def read_image(self, id, image_name, storeview_id=None):
        return self._call('product_media.info',
                          [int(id), image_name, storeview_id, 'id'])

    def update_inventory(self, id, data):
        # product_stock.update is too slow
        return self._call('oerp_cataloginventory_stock_item.update',
                          [int(id), data])


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
        to_date = filters.pop('to_date', None)
        record_ids = self.backend_adapter.search(filters,
                                                 from_date=from_date,
                                                 to_date=to_date)
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

    def _sort_images(self, images):
        """ Returns a list of images sorted by their priority.
        An image with the 'image' type is the the primary one.
        The other images are sorted by their position.

        The returned list is reversed, the items at the end
        of the list have the higher priority.
        """
        if not images:
            return {}
        # place the images where the type is 'image' first then
        # sort them by the reverse priority (last item of the list has
        # the the higher priority)

        def priority(image):
            primary = 'image' in image['types']
            try:
                position = int(image['position'])
            except ValueError:
                position = sys.maxint
            return (primary, -position)
        return sorted(images, key=priority)

    def _get_binary_image(self, image_data):
        url = image_data['url'].encode('utf8')
        try:
            request = urllib2.Request(url)
            if self.backend_record.auth_basic_username \
                    and self.backend_record.auth_basic_password:
                base64string = base64.encodestring(
                    '%s:%s' % (self.backend_record.auth_basic_username,
                               self.backend_record.auth_basic_password))
                request.add_header("Authorization", "Basic %s" % base64string)
            binary = urllib2.urlopen(request)
        except urllib2.HTTPError as err:
            if err.code == 404:
                # the image is just missing, we skip it
                return
            else:
                # we don't know why we couldn't download the image
                # so we propagate the error, the import will fail
                # and we have to check why it couldn't be accessed
                raise
        else:
            return binary.read()

    def run(self, magento_id, binding_id):
        self.magento_id = magento_id
        images = self._get_images()
        images = self._sort_images(images)
        binary = None
        while not binary and images:
            binary = self._get_binary_image(images.pop())
        if not binary:
            return
        with self.session.change_context({'connector_no_export': True}):
            self.session.write(self.model._name,
                               binding_id,
                               {'image': base64.b64encode(binary)})


@magento
class BundleImporter(ImportSynchronizer):
    """ Can be inherited to change the way the bundle products are
    imported.

    Called at the end of the import of a product.

    Example of action when importing a bundle product:
        - Create a bill of material
        - Import the structure of the bundle in new objects

    By default, the bundle products are not imported: the jobs
    are set as failed, because there is no known way to import them.
    An additional module that implements the import should be installed.

    If you want to create a custom importer for the bundles, you have to
    declare the ConnectorUnit on your backend::

        @magento_custom
        class XBundleImporter(BundleImporter):
            _model_name = 'magento.product.product'

            # implement import_bundle

    If you want to create a generic module that import bundles, you have
    to replace the current ConnectorUnit::

        @magento(replacing=BundleImporter)
        class XBundleImporter(BundleImporter):
            _model_name = 'magento.product.product'

            # implement import_bundle

    And to add the bundle type in the supported product types::

        class magento_product_product(orm.Model):
            _inherit = 'magento.product.product'

            def product_type_get(self, cr, uid, context=None):
                types = super(magento_product_product, self).product_type_get(
                    cr, uid, context=context)
                if 'bundle' not in [item[0] for item in types]:
                    types.append(('bundle', 'Bundle'))
                return types

    """
    _model_name = 'magento.product.product'

    def run(self, binding_id, magento_record):
        """ Import the bundle information about a product.

        :param magento_record: product information from Magento
        """


@magento
class ProductImport(MagentoImportSynchronizer):
    _model_name = ['magento.product.product']

    @property
    def mapper(self):
        if self._mapper is None:
            self._mapper = self.get_connector_unit_for_model(
                ProductImportMapper)
        return self._mapper

    def _import_bundle_dependencies(self):
        """ Import the dependencies for a Bundle """
        bundle = self.magento_record['_bundle_data']
        for option in bundle['options']:
            for selection in option['selections']:
                self._import_dependency(selection['product_id'],
                                        'magento.product.product')

    def _import_dependencies(self):
        """ Import the dependencies for the record"""
        record = self.magento_record
        # import related categories
        for mag_category_id in record['categories']:
            self._import_dependency(mag_category_id,
                                    'magento.product.category')
        if record['type_id'] == 'bundle':
            self._import_bundle_dependencies()

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

    def _must_skip(self):
        """ Hook called right after we read the data from the backend.

        If the method returns a message giving a reason for the
        skipping, the import will be interrupted and the message
        recorded in the job (if the import is called directly by the
        job, not by dependencies).

        If it returns None, the import will continue normally.

        :returns: None | str | unicode
        """
        if self.magento_record['type_id'] == 'configurable':
            return _('The configurable product is not imported in OpenERP, '
                     'because only the simple products are used in the sales '
                     'orders.')

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

    def _after_import(self, binding_id):
        """ Hook called at the end of the import """
        translation_importer = self.get_connector_unit_for_model(
            TranslationImporter, self.model._name)
        translation_importer.run(self.magento_id, binding_id,
                                 mapper_class=ProductImportMapper)
        image_importer = self.get_connector_unit_for_model(
            CatalogImageImporter, self.model._name)
        image_importer.run(self.magento_id, binding_id)

        if self.magento_record['type_id'] == 'bundle':
            bundle_importer = self.get_connector_unit_for_model(
                BundleImporter, self.model._name)
            bundle_importer.run(binding_id, self.magento_record)


@magento
class IsActiveProductImportMapper(ImportMapper):
    _model_name = 'magento.product.product'

    @mapping
    def is_active(self, record):
        """Check if the product is active in Magento
        and set active flag in OpenERP
        status == 1 in Magento means active"""
        return {'active': (record.get('status') == '1')}


@magento
class BundleProductImportMapper(ImportMapper):
    _model_name = 'magento.product.product'


@magento
class ProductImportMapper(ImportMapper):
    _model_name = 'magento.product.product'
    # TODO :     categ, special_price => minimal_price
    direct = [('name', 'name'),
              ('description', 'description'),
              ('weight', 'weight'),
              ('cost', 'standard_price'),
              ('short_description', 'description_sale'),
              ('sku', 'default_code'),
              ('type_id', 'product_type'),
              (normalize_datetime('created_at'), 'created_at'),
              (normalize_datetime('updated_at'), 'updated_at'),
              ]

    @mapping
    def is_active(self, record):
        mapper = self.get_connector_unit_for_model(IsActiveProductImportMapper)
        return mapper.map_record(record).values()

    @mapping
    def price(self, record):
        """ The price is imported at the creation of
        the product, then it is only modified and exported
        from OpenERP """
        return {'list_price': record.get('price', 0.0)}

    @mapping
    def type(self, record):
        if record['type_id'] == 'simple':
            return {'type': 'product'}
        return

    @mapping
    def website_ids(self, record):
        website_ids = []
        binder = self.get_binder_for_model('magento.website')
        for mag_website_id in record['websites']:
            website_id = binder.to_openerp(mag_website_id)
            website_ids.append((4, website_id))
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

    @mapping
    def bundle_mapping(self, record):
        if record['type_id'] == 'bundle':
            bundle_mapper = self.get_connector_unit_for_model(
                BundleProductImportMapper)
            return bundle_mapper.map_record(record).values()


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

    def run(self, binding_id, fields):
        """ Export the product inventory to Magento """
        product = self.session.browse(self.model._name, binding_id)
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
def magento_product_modified(session, model_name, record_id, vals):
    if session.context.get('connector_no_export'):
        return
    if session.browse(model_name, record_id).no_stock_sync:
        return
    inventory_fields = list(set(vals).intersection(INVENTORY_FIELDS))
    if inventory_fields:
        export_product_inventory.delay(session, model_name,
                                       record_id, fields=inventory_fields,
                                       priority=20)


@job
@related_action(action=unwrap_binding)
def export_product_inventory(session, model_name, record_id, fields=None):
    """ Export the inventory configuration and quantity of a product. """
    product = session.browse(model_name, record_id)
    backend_id = product.backend_id.id
    env = get_environment(session, model_name, backend_id)
    inventory_exporter = env.get_connector_unit(ProductInventoryExport)
    return inventory_exporter.run(record_id, fields)
