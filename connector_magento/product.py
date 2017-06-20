# -*- coding: utf-8 -*-
# © 2013 Guewen Baconnier,Camptocamp SA,Akretion
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import urllib2
import base64
import xmlrpclib
import sys

from collections import defaultdict

from odoo import models, fields, api, _
from odoo.addons.connector.event import on_record_write
from odoo.addons.connector.exception import (MappingError,
                                             InvalidDataError,
                                             IDMissingInBackend
                                             )
from odoo.addons.connector.components.mapper import mapping
from odoo.addons.component.core import Component
from odoo.addons.queue_job.job import job, related_action
from .components.backend_adapter import MAGENTO_DATETIME_FORMAT
from .components.mapper import normalize_datetime

_logger = logging.getLogger(__name__)


def chunks(items, length):
    for index in xrange(0, len(items), length):
        yield items[index:index + length]


class MagentoProductProduct(models.Model):
    _name = 'magento.product.product'
    _inherit = 'magento.binding'
    _inherits = {'product.product': 'odoo_id'}
    _description = 'Magento Product'

    @api.model
    def product_type_get(self):
        return [
            ('simple', 'Simple Product'),
            ('configurable', 'Configurable Product'),
            ('virtual', 'Virtual Product'),
            ('downloadable', 'Downloadable Product'),
            # XXX activate when supported
            # ('grouped', 'Grouped Product'),
            # ('bundle', 'Bundle Product'),
        ]

    odoo_id = fields.Many2one(comodel_name='product.product',
                              string='Product',
                              required=True,
                              ondelete='restrict')
    # XXX website_ids can be computed from categories
    website_ids = fields.Many2many(comodel_name='magento.website',
                                   string='Websites',
                                   readonly=True)
    created_at = fields.Date('Created At (on Magento)')
    updated_at = fields.Date('Updated At (on Magento)')
    product_type = fields.Selection(selection='product_type_get',
                                    string='Magento Product Type',
                                    default='simple',
                                    required=True)
    manage_stock = fields.Selection(
        selection=[('use_default', 'Use Default Config'),
                   ('no', 'Do Not Manage Stock'),
                   ('yes', 'Manage Stock')],
        string='Manage Stock Level',
        default='use_default',
        required=True,
    )
    backorders = fields.Selection(
        selection=[('use_default', 'Use Default Config'),
                   ('no', 'No Sell'),
                   ('yes', 'Sell Quantity < 0'),
                   ('yes-and-notification', 'Sell Quantity < 0 and '
                                            'Use Customer Notification')],
        string='Manage Inventory Backorders',
        default='use_default',
        required=True,
    )
    magento_qty = fields.Float(string='Computed Quantity',
                               help="Last computed quantity to send "
                                    "on Magento.")
    no_stock_sync = fields.Boolean(
        string='No Stock Synchronization',
        required=False,
        help="Check this to exclude the product "
             "from stock synchronizations.",
    )

    RECOMPUTE_QTY_STEP = 1000  # products at a time

    @job(default_channel='root.magento')
    @related_action(action='related_action_unwrap_binding')
    @api.multi
    def export_inventory(self, fields=None):
        """ Export the inventory configuration and quantity of a product. """
        self.ensure_one()
        with self.backend_id.work_on(self._name) as work:
            exporter = work.component(usage='product.inventory.exporter')
            return exporter.run(self, fields)

    @api.multi
    def recompute_magento_qty(self):
        """ Check if the quantity in the stock location configured
        on the backend has changed since the last export.

        If it has changed, write the updated quantity on `magento_qty`.
        The write on `magento_qty` will trigger an `on_record_write`
        event that will create an export job.

        It groups the products by backend to avoid to read the backend
        informations for each product.
        """
        # group products by backend
        backends = defaultdict(self.browse)
        for product in self:
            backends[product.backend_id] |= product

        for backend, products in backends.iteritems():
            self._recompute_magento_qty_backend(backend, products)
        return True

    @api.multi
    def _recompute_magento_qty_backend(self, backend, products,
                                       read_fields=None):
        """ Recompute the products quantity for one backend.

        If field names are passed in ``read_fields`` (as a list), they
        will be read in the product that is used in
        :meth:`~._magento_qty`.

        """
        if backend.product_stock_field_id:
            stock_field = backend.product_stock_field_id.name
        else:
            stock_field = 'virtual_available'

        location = backend.warehouse_id.lot_stock_id

        product_fields = ['magento_qty', stock_field]
        if read_fields:
            product_fields += read_fields

        self_with_location = self.with_context(location=location.id)
        for chunk_ids in chunks(products.ids, self.RECOMPUTE_QTY_STEP):
            records = self_with_location.browse(chunk_ids)
            for product in records.read(fields=product_fields):
                new_qty = self._magento_qty(product,
                                            backend,
                                            location,
                                            stock_field)
                if new_qty != product['magento_qty']:
                    self.browse(product['id']).magento_qty = new_qty

    @api.multi
    def _magento_qty(self, product, backend, location, stock_field):
        """ Return the current quantity for one product.

        Can be inherited to change the way the quantity is computed,
        according to a backend / location.

        If you need to read additional fields on the product, see the
        ``read_fields`` argument of :meth:`~._recompute_magento_qty_backend`

        """
        return product[stock_field]


class ProductProduct(models.Model):
    _inherit = 'product.product'

    magento_bind_ids = fields.One2many(
        comodel_name='magento.product.product',
        inverse_name='odoo_id',
        string='Magento Bindings',
    )


class ProductProductAdapter(Component):
    _name = 'magento.product.product.adapter'
    _inherit = 'magento.adapter'
    _apply_on = 'magento.product.product'

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


class ProductBatchImporter(Component):
    """ Import the Magento Products.

    For every product category in the list, a delayed job is created.
    Import from a date
    """
    _name = 'magento.product.product.batch.importer'
    _inherit = 'magento.delayed.batch.importer'
    _apply_on = ['magento.product.product']

    def run(self, filters=None):
        """ Run the synchronization """
        from_date = filters.pop('from_date', None)
        to_date = filters.pop('to_date', None)
        external_ids = self.backend_adapter.search(filters,
                                                   from_date=from_date,
                                                   to_date=to_date)
        _logger.info('search for magento products %s returned %s',
                     filters, external_ids)
        for external_id in external_ids:
            self._import_record(external_id)


class CatalogImageImporter(Component):
    """ Import images for a record.

    Usually called from importers, in ``_after_import``.
    For instance from the products importer.
    """
    _name = 'magento.product.image.importer'
    _inherit = 'magento.importer'
    _apply_on = ['magento.product.product']
    _usage = 'product.image.importer'

    def _get_images(self, storeview_id=None):
        return self.backend_adapter.get_images(self.external_id, storeview_id)

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
                position = sys.maxsize
            return (primary, -position)
        return sorted(images, key=priority)

    def _get_binary_image(self, image_data):
        url = image_data['url'].encode('utf8')
        try:
            request = urllib2.Request(url)
            if self.backend_record.auth_basic_username \
                    and self.backend_record.auth_basic_password:
                base64string = base64.b64encode(
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

    def _write_image_data(self, binding, binary, image_data):
        binding = binding.with_context(connector_no_export=True)
        binding.write({'image': base64.b64encode(binary)})

    def run(self, external_id, binding):
        self.external_id = external_id
        images = self._get_images()
        images = self._sort_images(images)
        binary = None
        image_data = None
        while not binary and images:
            image_data = images.pop()
            binary = self._get_binary_image(image_data)
        if not binary:
            return
        self._write_image_data(binding, binary, image_data)


# TODO: not needed, use inheritance
class BundleImporter(Component):
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
    inherit the Component::

        class BundleImporter(Component):
            _inherit = 'magento.product.bundle.importer'

    And to add the bundle type in the supported product types::

        class MagentoProductProduct(models.Model):
            _inherit = 'magento.product.product'

            @api.model
            def product_type_get(self):
                types = super(MagentoProductProduct, self).product_type_get()
                if 'bundle' not in [item[0] for item in types]:
                    types.append(('bundle', 'Bundle'))
                return types

    """
    _name = 'magento.product.bundle.importer'
    _inherit = 'magento.importer'
    _apply_on = ['magento.product.product']
    _usage = 'product.bundle.importer'

    def run(self, binding, magento_record):
        """ Import the bundle information about a product.

        :param magento_record: product information from Magento
        """


class ProductImportMapper(Component):
    _name = 'magento.product.product.import.mapper'
    _inherit = 'magento.import.mapper'
    _apply_on = ['magento.product.product']

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
        """Check if the product is active in Magento
        and set active flag in OpenERP
        status == 1 in Magento means active"""
        return {'active': (record.get('status') == '1')}

    @mapping
    def price(self, record):
        return {'list_price': record.get('price', 0.0)}

    @mapping
    def type(self, record):
        if record['type_id'] == 'simple':
            return {'type': 'product'}
        elif record['type_id'] in ('virtual', 'downloadable'):
            return {'type': 'service'}
        return

    @mapping
    def website_ids(self, record):
        website_ids = []
        binder = self.binder_for('magento.website')
        for mag_website_id in record['websites']:
            website_binding = binder.to_internal(mag_website_id)
            website_ids.append((4, website_binding.id))
        return {'website_ids': website_ids}

    @mapping
    def categories(self, record):
        mag_categories = record['categories']
        binder = self.binder_for('magento.product.category')

        category_ids = []
        main_categ_id = None

        for mag_category_id in mag_categories:
            cat = binder.to_internal(mag_category_id, unwrap=True)
            if not cat:
                raise MappingError("The product category with "
                                   "magento id %s is not imported." %
                                   mag_category_id)

            category_ids.append(cat.id)

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
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}


class ProductImporter(Component):
    _name = 'magento.product.product.importer'
    _inherit = 'magento.importer'
    _apply_on = ['magento.product.product']

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
        product_type = data['product_type']
        product_model = self.env['magento.product.product']
        types = product_model.product_type_get()
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
            return _('The configurable product is not imported in Odoo, '
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
        binding = super(ProductImporter, self)._create(data)
        self.backend_record.add_checkpoint(binding)
        return binding

    def _after_import(self, binding):
        """ Hook called at the end of the import """
        translation_importer = self.component(
            usage='translation.importer',
        )
        translation_importer.run(
            self.external_id,
            binding,
            mapper='magento.product.product.import.mapper'
        )
        image_importer = self.component(usage='product.image.importer')
        image_importer.run(self.external_id, binding)

        if self.magento_record['type_id'] == 'bundle':
            bundle_importer = self.component(usage='product.bundle.importer')
            bundle_importer.run(binding, self.magento_record)


class ProductInventoryExporter(Component):
    _name = 'magento.product.product.exporter'
    _inherit = 'magento.exporter'
    _apply_on = ['magento.product.product']
    _usage = 'product.inventory.exporter'

    _map_backorders = {'use_default': 0,
                       'no': 0,
                       'yes': 1,
                       'yes-and-notification': 2,
                       }

    def _get_data(self, binding, fields):
        result = {}
        if 'magento_qty' in fields:
            result.update({
                'qty': binding.magento_qty,
                # put the stock availability to "out of stock"
                'is_in_stock': int(binding.magento_qty > 0)
            })
        if 'manage_stock' in fields:
            manage = binding.manage_stock
            result.update({
                'manage_stock': int(manage == 'yes'),
                'use_config_manage_stock': int(manage == 'use_default'),
            })
        if 'backorders' in fields:
            backorders = binding.backorders
            result.update({
                'backorders': self._map_backorders[backorders],
                'use_config_backorders': int(backorders == 'use_default'),
            })
        return result

    def run(self, binding, fields):
        """ Export the product inventory to Magento """
        external_id = self.binder.to_external(binding)
        data = self._get_data(binding, fields)
        self.backend_adapter.update_inventory(external_id, data)


# fields which should not trigger an export of the products
# but an export of their inventory
INVENTORY_FIELDS = ('manage_stock',
                    'backorders',
                    'magento_qty',
                    )


@on_record_write(model_names=['magento.product.product'])
def magento_product_modified(env, model_name, record_id, vals):
    if env.context.get('connector_no_export'):
        return
    binding = env[model_name].browse(record_id)
    if binding.no_stock_sync:
        return
    inventory_fields = list(set(vals).intersection(INVENTORY_FIELDS))
    if inventory_fields:
        binding.with_delay(priority=20).export_inventory(
            fields=inventory_fields
        )
