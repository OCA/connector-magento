# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging
from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create
from odoo.addons.connector.exception import MappingError, InvalidDataError
from odoo.addons.queue_job.exception import NothingToDoJob

_logger = logging.getLogger(__name__) 


class ProductBundleBatchImporter(Component):
    """ Import the Magento bundle Products.

    For every product bundle in the list, a delayed job is created.
    Import from a date
    """
    _name = 'magento.product.bundle.batch.importer'
    _inherit = 'magento.delayed.batch.importer'
    _apply_on = ['magento.product.bundle']

    def run(self, filters=None):
        """ Run the synchronization """
        from_date = filters.pop('from_date', None)
        to_date = filters.pop('to_date', None)
        # Variants to have visibility=1
        filters['visibility'] = {'eq': 4}
        filters['type_id'] = {'eq': 'bundle'}
        filters['status'] = {'eq': 1}
        external_ids = self.backend_adapter.search(filters,
                                                   from_date=from_date,
                                                   to_date=to_date)
        _logger.info('search for magento product bundles %s returned %s',
                     filters, external_ids)
        for external_id in external_ids:
            self._import_record(external_id)


class MagentoProductBundleImageImporter(Component):
    """ Import images for a record.

    Usually called from importers, in ``_after_import``.
    For instance from the products importer.
    """
    _name = 'magento.product.bundle.image.importer'
    _inherit = 'magento.product.image.importer'
    _apply_on = ['magento.product.bundle']
    _usage = 'bundle.image.importer'


class ProductBundleImporter(Component):
    _name = 'magento.product.bundle.importer'
    _inherit = 'magento.importer'
    _apply_on = ['magento.product.bundle']

    def _create(self, data):
        # create_product_product - Avoid creating variant products
        binding = super(ProductBundleImporter, self)._create(data)
        self.backend_record.add_checkpoint(binding)
        return binding

    def _import_dependency(self, external_id, binding_model,
                           importer=None, always=False, binding_bundle_id=None, external_field=None):
        """ Import a dependency.

        The importer class is a class or subclass of
        :class:`MagentoImporter`. A specific class can be defined.

        :param external_id: id of the related binding to import
        :param binding_model: name of the binding model for the relation
        :type binding_model: str | unicode
        :param importer_component: component to use for import
                                   By default: 'importer'
        :type importer_component: Component
        :param always: if True, the record is updated even if it already
                       exists, note that it is still skipped if it has
                       not been modified on Magento since the last
                       update. When False, it will import it only when
                       it does not yet exist.
        :type always: boolean
        """
        if not external_id:
            return
        binder = self.binder_for(binding_model)
        if always or not binder.to_internal(external_id, external_field=external_field):
            if importer is None:
                importer = self.component(usage='record.importer',
                                          model_name=binding_model)
            try:
                if binding_model == "magento.product.product":
                    importer.run(external_id, binding_bundle_id=binding_bundle_id)
                else:
                    importer.run(external_id)
            except NothingToDoJob:
                _logger.info(
                    'Dependency import of %s(%s) has been ignored.',
                    binding_model._name, external_id
                )

    def _update_price(self, binding, price):
        # Update price if price is 0
        if binding.price == 0:
            binding.price = price

    def _import_options(self, binding):
        record = self.magento_record
        moptions = record['extension_attributes']['bundle_product_options']
        option_importer = self.component(usage='record.importer',
                                         model_name='magento.bundle.option')
        for moption in moptions:
            # Do always import / update
            option_importer.run(moption, bundle_binding=binding)

    def _get_binding(self):
        binding = super(ProductBundleImporter, self)._get_binding()
        if not binding:
            # Do search using the magento_id - maybe the sku did changed !
            binding = self.env['magento.product.bundle'].search([
                ('backend_id', '=', self.backend_record.id),
                ('magento_id', '=', self.magento_record['id']),
            ])
            # if we found binding here - then the update will also update the external_id on the binding record
        return binding

    def _after_import(self, binding):
        # Import Images
        image_importer = self.component(usage='bundle.image.importer')
        image_importer.run(self.external_id, binding,
                           data=self.magento_record)
        #TODO Import Bundles
        self._import_options(binding)

        # Do also import translations
        translation_importer = self.component(
            usage='translation.importer',
        )
        translation_importer.run(
            self.external_id,
            binding,
            mapper='magento.product.bundle.import.mapper'
        )

    def _is_uptodate(self, binding):
        # TODO: Remove for production - only to test the update
        return False

    def _import_dependencies(self):
        record = self.magento_record
        # Import attribute deps
        for attribute in record.get('custom_attributes'):
            # We do search binding using attribute_code - default is attribute_id !
            self._import_dependency(attribute['attribute_code'],
                                    'magento.product.attribute', external_field='attribute_code')


class ProductBundleImportMapper(Component):
    _name = 'magento.product.bundle.import.mapper'
    _inherit = 'magento.product.product.import.mapper'
    _apply_on = ['magento.product.bundle']

    @mapping
    def categories(self, record):
        # No categories on configurable product
        category_links = record['extension_attributes']['category_links']
        binder = self.binder_for('magento.product.category')
        category_ids = []
        main_categ_id = None
        # TODO: Read also position !
        for category_link in category_links:
            cat = binder.to_internal(category_link['category_id'], unwrap=True)
            if not cat:
                raise MappingError("The product category with "
                                   "magento id %s is not imported." %
                                   category_link['category_id'])

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
    def auto_create_variants(self, record):
        # By default we disable auto create variants when product is coming from a webshop
        # TODO: Make this configurable using the backend record !
        return {
            'auto_create_variants': False
        }

    @mapping
    def price(self, record):
        return {
            'list_price': record.get('price', 0.0),
        }

    @mapping
    def cost(self, record):
        return {
            'standard_price': record.get('cost', 0.0),
        }

    @mapping
    def product_name(self, record):
        return {
            'name': record.get('name', ''),
        }

    @only_create
    @mapping
    def odoo_id(self, record):
        """ Will bind the product to an existing one with the same code """
        product = self.env['product.product'].search(
            [('default_code', '=', record['sku'])], limit=1)
        if product:
            return {'odoo_id': product.id}

    @mapping
    def odoo_type(self, record):
        return {'type': 'bundle'}

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
                    searchn = u'_'.join((att.external_id,str(record.get(att.name)))).encode('utf-8')
                except UnicodeEncodeError:
                    searchn = u'_'.join((att.external_id,record.get(att.name))).encode('utf-8')
                att_val = self.env['magento.product.attribute.value'].search(
                    [('external_id', '=', searchn)], limit=1)
                _logger.debug("Import custom att_val %r %r " % (att_val, searchn ))
                if att_val:
                    link_value.append(att_val[0].odoo_id.id)
        #TODO: Switch between standr Odoo class or to the new class
        return {'attribute_set_id': attribute_set.id,'attribute_value_ids': [(6,0,link_value)]}


class ProductBundleOptionImporter(Component):
    _name = 'magento.bundle.option.importer'
    _inherit = 'magento.importer'
    _magento_id_field = 'option_id'
    _apply_on = ['magento.bundle.option']

    def _create_data(self, map_record, **kwargs):
        return map_record.values(for_create=True, bundle_binding=self.bundle_binding, **kwargs)

    def _update_data(self, map_record, **kwargs):
        return map_record.values(bundle_binding=self.bundle_binding, **kwargs)

    def run(self, external_id, force=False, bundle_binding=None):
        self.bundle_binding = bundle_binding
        return super(ProductBundleOptionImporter, self).run(external_id, force)


class ProductBundleOptionImportMapper(Component):
    _name = 'magento.bundle.option.import.mapper'
    _inherit = 'magento.import.mapper'
    _apply_on = ['magento.bundle.option']

    direct = [
        ('title', 'title'),
        ('required', 'required'),
        ('type', 'type'),
        ('position', 'position'),
    ]

    children = [
        ('product_links', 'option_product_ids', 'magento.bundle.option.product'),
    ]

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}

    @mapping
    def magento_bundle_id(self, record):
        return {'magento_bundle_id': self.options.bundle_binding.id}


class ProductBundleOptionProductImportMapper(Component):
    _name = 'magento.bundle.option.product.import.mapper'
    _inherit = 'magento.import.mapper'
    _apply_on = ['magento.bundle.option.product']

    direct = [
        ('id', 'external_id'),
        ('qty', 'qty'),
        ('is_default', 'is_default'),
        ('price', 'price'),
        ('position', 'position'),
        ('price_type', 'price_type'),
        ('can_change_quantity', 'can_change_quantity'),
    ]

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}

    @mapping
    def magento_product_id(self, record):
        binder = self.binder_for('magento.product.product')
        mproduct = binder.to_internal(record['sku'])
        if not mproduct:
            raise MappingError("The product with sku %s "
                               "is not imported." %
                               record['sku'])

        return {'magento_product_id': mproduct.id}

    def finalize(self, map_record, values):
        # Search for existing entry
        binder = self.binder_for(model='magento.bundle.option.product')
        magento_option_product = binder.to_internal(values['external_id'], unwrap=False)
        if magento_option_product:
            values.update({'id': magento_option_product.id})
        return values


class ProductBundleOptionProductMapChild(Component):
    _name = 'magento.bundle.option.product.map.child.import'
    _inherit = 'base.map.child.import'
    _apply_on = ['magento.bundle.option.product']

    def format_items(self, items_values):
        """ Format the values of the items mapped from the child Mappers.

        It can be overridden for instance to add the Odoo
        relationships commands ``(6, 0, [IDs])``, ...

        As instance, it can be modified to handle update of existing
        items: check if an 'id' has been defined by
        :py:meth:`get_item_values` then use the ``(1, ID, {values}``)
        command

        :param items_values: list of values for the items to create
        :type items_values: list

        """
        res = []
        for values in items_values:
            if 'id' in values:
                id = values.pop('id')
                res.append((1, id, values))
            else:
                res.append((0, 0, values))
        return res
