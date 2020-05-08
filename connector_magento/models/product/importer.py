# Copyright 2013-2019 Camptocamp SA
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging
import requests
import base64
import sys

from odoo import _
from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create
from odoo.addons.connector.exception import MappingError, InvalidDataError
from ...components.mapper import normalize_datetime

_logger = logging.getLogger(__name__)


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

    def _get_images(self, storeview_id=None, data=None):
        return self.backend_adapter.get_images(
            self.external_id, storeview_id, data=data)

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
        url = image_data['url']
        headers = {}
        if self.backend_record.auth_basic_username \
           and self.backend_record.auth_basic_password:
            base64string = base64.b64encode(("%s:%s" % (
                self.backend_record.auth_basic_username,
                self.backend_record.auth_basic_password)
            ).encode('utf-8'))
            headers["Authorization"] = "Basic %s" % (
                base64string.decode('utf-8'))
        request = requests.get(
            url, headers=headers, verify=self.backend_record.verify_ssl)
        if request.status_code == 404:
            # the image is just missing, we skip it
            return
        # On any other error, we don't know why we couldn't download the
        # image so we propagate the error, the import will fail and we
        # have to check why it couldn't be accessed
        request.raise_for_status()
        return request.content

    def _write_image_data(self, binding, binary, image_data):
        binding = binding.with_context(connector_no_export=True)
        binding.write({'image': base64.b64encode(binary)})

    def run(self, external_id, binding, data=None):
        self.external_id = external_id
        images = self._get_images(data=data)
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
              ('id', 'magento_internal_id'),
              ('description', 'description'),
              ('weight', 'weight'),
              ('cost', 'standard_price'),
              ('short_description', 'description_sale'),
              ('sku', 'default_code'),
              ('type_id', 'product_type'),
              (normalize_datetime('created_at'), 'created_at'),
              (normalize_datetime('updated_at'), 'updated_at'),
              ]

    @only_create
    @mapping
    def odoo_id(self, record):
        """ Will bind the product to an existing one with the same code """
        product = self.env['product.product'].search(
            [('default_code', '=', record['sku'])], limit=1)
        if product:
            return {'odoo_id': product.id}

    @mapping
    def external_id(self, record):
        """ Magento 2 to use sku as external id, because this is used as the
        slug in the product REST API """
        if self.collection.version == '2.0':
            return {'external_id': record['sku']}

    @mapping
    def is_active(self, record):
        """Check if the product is active in Magento
        and set active flag in OpenERP
        status == 1 in Magento means active.
        Magento 2.x returns an integer, 1.x a string """
        return {'active': (record.get('status') in (1, '1'))}

    @mapping
    def price(self, record):
        return {'list_price': record.get('price', 0.0)}

    @mapping
    def type(self, record):
        if record['type_id'] == 'simple':
            return {'type': 'product'}
        elif record['type_id'] in ('virtual', 'downloadable', 'giftcard'):
            return {'type': 'service'}
        return

    @mapping
    def website_ids(self, record):
        """ Websites are not returned in Magento 2.x, see
        https://github.com/magento/magento2/issues/3864 """
        website_ids = []
        binder = self.binder_for('magento.website')
        for mag_website_id in record.get('websites', []):
            website_binding = binder.to_internal(mag_website_id)
            website_ids.append((4, website_binding.id))
        return {'website_ids': website_ids}

    @mapping
    def categories(self, record):
        """ Fetch categories key for Magento 1.x or category_ids
        for Magento 2.x from product record """
        mag_categories = record.get('category_ids') or record.get(
            'categories', [])
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
        if self.collection.version == '1.7':
            for dependency in [
                    selection for option in
                    self.magento_record['_bundle_data']['options']
                    for selection in option['selections']]:
                self._import_dependency(dependency['product_id'],
                                        'magento.product.product')
        else:
            for dependency in [
                    product_link for option in self.magento_record[
                        'extension_attributes']['bundle_product_options']
                    for product_link in option['product_links']]:
                self._import_dependency(dependency['sku'],
                                        'magento.product.product')

    def _import_dependencies(self):
        """ Import the dependencies for the record"""
        record = self.magento_record
        # import related categories
        for mag_category_id in (record.get('category_ids') or record.get(
                'categories', [])):
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
        binding = super()._create(data)
        if not binding.active:
            # Disable reordering rules that has been created automatically
            binding.orderpoint_ids.write({'active': False})
        self.backend_record.add_checkpoint(binding)
        return binding

    def _update(self, binding, data):
        # enable/disable reordering rules before updating the product as Odoo
        # do not allow to disable a product while having active reordering
        # rules on it
        if 'active' in data and not data.get('active'):
            binding.mapped('orderpoint_ids').write({'active': False})
        res = super()._update(binding, data)
        return res

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
        image_importer.run(self.external_id, binding, data=self.magento_record)

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
