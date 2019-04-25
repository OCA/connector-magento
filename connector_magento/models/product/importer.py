# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
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
        # with visibility=4 we only get products which are standalone products - product variants have visibility=1 !
        filters['visibility'] = {'eq': 4}
        filters['type_id'] = {'eq': 'simple'}
        filters['status'] = {'eq': 1}
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
        if self.work.magento_api._location.version == '2.0':
            if 'magento.product.product' in self._apply_on:
                model = 'product'
            elif 'magento.product.template' in self._apply_on:
                model = 'product'
            elif 'magento.product.bundle' in self._apply_on:
                model = 'product'
            else:
                raise NotImplementedError  # Categories?
            image_data['url'] = '%s/pub/media/catalog/%s/%s' % (
                self.backend_record.location, model, image_data['file'])
        url = image_data['url'].encode('utf8')
        headers = {}
        if (self.backend_record.auth_basic_username and
                self.backend_record.auth_basic_password):
            base64string = base64.b64encode(
                '%s:%s' % (self.backend_record.auth_basic_username,
                           self.backend_record.auth_basic_password))
            headers['Authorization'] = "Basic %s" % base64string
        # TODO: make verification of ssl a backend setting
        request = requests.get(url, headers=headers,
                               verify=self.backend_record.verify_ssl)
        if request.status_code == 404:
            # the image is just missing, we skip it
            return
        else:
            # we don't know why we couldn't download the image
            # so we propagate the error, the import will fail
            # and we have to check why it couldn't be accessed
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
    direct = [('name', 'magento_name'),
              ('price', 'magento_price'),
              ('description', 'description'),
              ('weight', 'weight'),
              ('short_description', 'description_sale'),
              ('sku', 'default_code'),
              ('sku', 'external_id'),
              ('type_id', 'product_type'),
              ('id', 'magento_id'),
              (normalize_datetime('created_at'), 'created_at'),
              (normalize_datetime('updated_at'), 'updated_at'),
              ]

    @mapping
    def is_active(self, record):
        """Check if the product is active in Magento
        and set active flag in Odoo. Status == 1 in Magento means active.
        2.0 REST API returns an integer, 1.x a string. """
        return {'active': (record.get('status') in ('1', 1))}

    @mapping
    def price(self, record):
        if record['visibility'] == 1:
            # This is a product variant - so the price got set on the template !
            return {}
        return {
            'list_price': record.get('price', 0.0),
        }

    @mapping
    def cost(self, record):
        if record['visibility'] == 1:
            # This is a product variant - so the price got set on the template !
            return {}
        return {
            'standard_price': record.get('cost', 0.0),
        }

    @mapping
    def product_name(self, record):
        if record['visibility'] == 1:
            # This is a product variant - so the price got set on the template !
            return {}
        return {
            'name': record.get('name', ''),
        }

    @mapping
    def tax_class_id(self, record):
        tax_attribute = [a for a in record['custom_attributes'] if a['attribute_code'] == 'tax_class_id']
        if not tax_attribute:
            return {}
        binder = self.binder_for('magento.account.tax')
        tax = binder.to_internal(tax_attribute[0]['value'], unwrap=True)
        if not tax:
            raise MappingError("The tax class with the id %s "
                               "is not imported." %
                               tax_attribute[0]['value'])
        return {'taxes_id': [(4, tax.id)]}

    @mapping
    def attributes(self, record):
        attribute_binder = self.binder_for('magento.product.attribute')
        value_binder = self.binder_for('magento.product.attribute.value')
        attribute_value_ids = []
        for attribute in record['custom_attributes']:
            mattribute = attribute_binder.to_internal(attribute['attribute_code'], unwrap=False, external_field='attribute_code')
            if not mattribute.create_variant:
                # We do ignore attributes which do not create a variant
                continue
            if not mattribute:
                raise MappingError("The product attribute %s is not imported." %
                                   mattribute.name)
            mvalue = value_binder.to_internal("%s_%s" % (mattribute.attribute_id, str(attribute['value'])), unwrap=False)
            if not mvalue:
                raise MappingError("The product attribute value %s in attribute %s is not imported." %
                                   (str(attribute['value']), mattribute.name))
            attribute_value_ids.append((4, mvalue.odoo_id.id))
        return {
            'attribute_value_ids': attribute_value_ids,
        }
        
    @mapping
    def custom_attributes(self, record):
        """
        Usefull with catalog exporter module 
        has to be migrated
        """
        attribute_binder = self.binder_for('magento.product.attribute')
        value_binder = self.binder_for('magento.product.attribute.value')
        magento_attribute_line_ids = []
        for attribute in record['custom_attributes']:
            mattribute = attribute_binder.to_internal(attribute['attribute_code'], unwrap=False, external_field='attribute_code')
            if mattribute.create_variant :
                # We do ignore attributes which do not create a variant
                continue
            if not mattribute:
                raise MappingError("The product attribute %s is not imported." %
                                   mattribute.name)
        
            vals = {
                #                 'backend_id': self.backend_id.id,
#                 'magento_product_id': mg_prod_id.id,
                'attribute_id': mattribute.id,
                'store_view_id': False,
                'attribute_text': attribute['value']
            }
            magento_attribute_line_ids.append((0, False, vals))
        return {
            'magento_attribute_line_ids': magento_attribute_line_ids
        }

    @mapping
    def type(self, record):
        if record['type_id'] == 'simple':
            return {'type': 'product'}
        elif record['type_id'] in ('virtual', 'downloadable', 'giftcard'):
            return {'type': 'service'}
        return

    @mapping
    def website_ids(self, record):
        if self.work.magento_api._location.version == '2.0':
            # https://github.com/magento/magento2/issues/3864
            return {}
        website_ids = []
        binder = self.binder_for('magento.website')
        for mag_website_id in record['websites']:
            website_binding = binder.to_internal(mag_website_id)
            website_ids.append((4, website_binding.id))
        return {'website_ids': website_ids}

    @mapping
    def categories(self, record):
        mag_categories = record.get('categories', record['category_ids'])
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
    def attribute_set_id(self, record):
        binder = self.binder_for('magento.product.attributes.set')
        attribute_set = binder.to_internal(record['attribute_set_id'])

        _logger.debug("-------------------------------------------> Import custom attributes %r" % attribute_set)
        link_value = []
        for att in attribute_set.attribute_ids:
            _logger.debug("Import custom att %r" % att)

            if record.get(att.name):
                try:
                    searchn = u'_'.join((att.external_id, str(record.get(att.name)))).encode('utf-8')
                except UnicodeEncodeError:
                    searchn = u'_'.join((att.external_id, record.get(att.name))).encode('utf-8')
                att_val = self.env['magento.product.attribute.value'].search(
                    [('external_id', '=', searchn)], limit=1)
                _logger.debug("Import custom att_val %r %r " % (att_val, searchn))
                if att_val:
                    link_value.append(att_val[0].odoo_id.id)
        # TODO: Switch between standr Odoo class or to the new class
        return {'attribute_set_id': attribute_set.id, 'attribute_value_ids': [(6, 0, link_value)]}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}

    @only_create
    @mapping
    def odoo_id(self, record):
        """ Will bind the product to an existing one with the same code """
        product = self.env['product.product'].search(
            [('default_code', '=', record['sku'])], limit=1)
        if product:
            return {'odoo_id': product.id}


class ProductImporter(Component):
    _name = 'magento.product.product.importer'
    _inherit = 'magento.importer'
    _apply_on = ['magento.product.product']
    _magento_id_field = 'sku'

    def _is_uptodate(self, binding):
        # TODO: Remove for production - only to test the update
        return False

    def _import_bundle_dependencies(self):
        """ Import the dependencies for a Bundle """
        bundle = self.magento_record['_bundle_data']
        for option in bundle['options']:
            for selection in option['selections']:
                self._import_dependency(selection['product_id'],
                                        'magento.product.product')

    def _import_stock_warehouse(self):
        record = self.magento_record
        stock_item = record['extension_attributes']['stock_item']
        binder = self.binder_for('magento.stock.warehouse')
        mwarehouse = binder.to_internal(stock_item['stock_id'])
        if not mwarehouse:
            # We do create the warehouse binding directly here - did not found a mapping on magento api
            binding = self.env['magento.stock.warehouse'].create({
                'backend_id': self.backend_record.id,
                'external_id': stock_item['stock_id'],
                'odoo_id': self.env['stock.warehouse'].search([('company_id', '=', self.backend_record.company_id.id)], limit=1).id,
            })
            self.backend_record.add_checkpoint(binding)

    def _import_dependencies(self):
        """ Import the dependencies for the record"""
        record = self.magento_record
        # import related categories
        for mag_category_id in record.get(
                'categories', record['category_ids']):
            self._import_dependency(mag_category_id,
                                    'magento.product.category')
        for attribute in record.get('custom_attributes'):
            # It will only import if it does not already exists - so it is safe to call it here
            # With always=True it will force the import / update
            self._import_dependency(attribute['attribute_code'],
                                    'magento.product.attribute', external_field='attribute_code')
        if record['type_id'] == 'bundle':
            self._import_bundle_dependencies()

        self._import_stock_warehouse()

    def _validate_product_type(self, data):
        """ Check if the product type is in the selection (so we can
        prevent the `except_orm` and display a better error message).
        """
        product_type = data['product_type']
        product_model = self.env['magento.product.template']
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

    def run(self, external_id, force=False, binding_template_id=None, binding=None):
        self._binding_template_id = binding_template_id
        return super(ProductImporter, self).run(external_id, force, binding=binding)

    def _update(self, binding, data):
        if self._binding_template_id:
            data['product_tmpl_id'] = self._binding_template_id.odoo_id.id
            data['magento_configurable_id'] = self._binding_template_id.id
            # Name is set on product template on configurables
            if 'name' in data:
                del data['name']
        super(ProductImporter, self)._update(binding, data)
        return

    def _create(self, data):
        if self._binding_template_id:
            data['product_tmpl_id'] = self._binding_template_id.odoo_id.id
            data['magento_configurable_id'] = self._binding_template_id.id
            # Name is set on product template on configurables
            if 'name' in data:
                del data['name']
        binding = super(ProductImporter, self)._create(data)
        self.backend_record.add_checkpoint(binding)
        return binding

    def _after_import(self, binding):
        def sort_by_position(elem):
            return elem.position

        """ Hook called at the end of the import """
        translation_importer = self.component(
            usage='translation.importer',
        )
        translation_importer.run(
            self.external_id,
            binding,
            mapper='magento.product.product.import.mapper'
        )

        media_importer = self.component(usage='product.media.importer', model_name='magento.product.media')
        for media in self.magento_record['media_gallery_entries']:
            media_importer.run(media, binding)
        # Here do choose the image at the smallest position as the main image
        for media_binding in sorted(binding.magento_image_bind_ids.filtered(lambda m: m.media_type == 'image'), key=sort_by_position):
            binding.with_context(connector_no_export=True).image = media_binding.image
            break
        '''
        image_importer = self.component(usage='product.image.importer')
        image_importer.run(self.external_id, binding,
                           data=self.magento_record)

        '''
        if self.magento_record['type_id'] == 'bundle':
            bundle_importer = self.component(usage='product.bundle.importer')
            bundle_importer.run(binding, self.magento_record)
        # Do import stock item
        stock_importer = self.component(usage='record.importer',
                                        model_name='magento.stock.item')
        stock_importer.run(self.magento_record['extension_attributes']['stock_item'])
