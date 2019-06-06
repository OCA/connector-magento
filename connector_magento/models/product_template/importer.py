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


class ProductTemplateBatchImporter(Component):
    """ Import the Magento configureable Products.

    For every product template in the list, a delayed job is created.
    Import from a date
    """
    _name = 'magento.product.template.batch.importer'
    _inherit = 'magento.delayed.batch.importer'
    _apply_on = ['magento.product.template']

    def run(self, filters=None):
        """ Run the synchronization """
        from_date = filters.pop('from_date', None)
        to_date = filters.pop('to_date', None)
        # Variants to have visibility=1
        filters['visibility'] = {'eq': 4}
        filters['type_id'] = {'eq': 'configurable'}
        filters['status'] = {'eq': 1}
        external_ids = self.backend_adapter.search(filters,
                                                   from_date=from_date,
                                                   to_date=to_date)
        _logger.info('search for magento product templates %s returned %s',
                     filters, external_ids)
        for external_id in external_ids:
            self._import_record(external_id)


class MagentoProductTemplateImageImporter(Component):
    """ Import images for a record.

    Usually called from importers, in ``_after_import``.
    For instance from the products importer.
    """
    _name = 'magento.product.template.image.importer'
    _inherit = 'magento.product.image.importer'
    _apply_on = ['magento.product.template']
    _usage = 'template.image.importer'


class ProductTemplateImporter(Component):
    _name = 'magento.product.template.importer'
    _inherit = 'magento.importer'
    _apply_on = ['magento.product.template']
    _magento_id_field = 'sku'

    def _create(self, data):
        # create_product_product - Avoid creating variant products
        binding = super(ProductTemplateImporter, self)._create(data)
        self.backend_record.add_checkpoint(binding)
        return binding

    def _import_dependency(self, external_id, binding_model,
                           importer=None, always=False, binding_template_id=None, external_field=None):
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
                    importer.run(external_id, binding_template_id=binding_template_id)
                else:
                    importer.run(external_id)
            except NothingToDoJob:
                _logger.info(
                    'Dependency import of %s(%s) has been ignored.',
                    binding_model._name, external_id
                )

    def _preprocess_magento_record(self):
        for attr in self.magento_record.get('custom_attributes', []):
            self.magento_record[attr['attribute_code']] = attr['value']
        return

    def _update_price(self, binding, price):
        # Update price if price is 0
        if binding.price == 0:
            binding.with_context(connector_no_export=True).price = price

    def _after_import(self, binding):
        def sort_by_position(elem):
            return elem.position

        # Import Images
        media_importer = self.component(usage='product.media.importer', model_name='magento.product.media')
        for media in self.magento_record['media_gallery_entries']:
            media_importer.run(media, binding)
        # Here do choose the image at the smallest position as the main image
        for media_binding in sorted(binding.magento_image_bind_ids.filtered(lambda m: m.media_type == 'image'), key=sort_by_position):
            binding.with_context(connector_no_export=True).image = media_binding.image
            break
        '''
        image_importer = self.component(usage='template.image.importer')
        image_importer.run(self.external_id, binding,
                           data=self.magento_record)
        '''
        # Import variants
        magento_variants = self.backend_adapter.list_variants(self.external_id)
        variant_binder = self.binder_for('magento.product.product')
        templates_delete = {}
        price = 0
        for magento_variant in magento_variants:
            if not price or magento_variant['price'] < price:
                price = magento_variant['price']
            # Search by sku - because this is also what is available in the mapper !
            variant = variant_binder.to_internal(magento_variant['sku'], unwrap=False)
            # Import / Update the variant here
            if not variant:
                # Pass product_template_id in arguments - so the product mapper will map it
                self._import_dependency(magento_variant['sku'], 'magento.product.product', always=True,
                                        binding_template_id=binding)
            elif variant.odoo_id.product_tmpl_id.id != binding.odoo_id.id:
                # Variant does exists already - and is at wrong odoo template - so reassign it - and delete old template
                old_template = variant.odoo_id.product_tmpl_id
                variant.odoo_id.product_tmpl_id = binding.odoo_id.id
                templates_delete[old_template.id] = old_template
            if variant:
                # Update the variant
                updater = self.component(usage='record.importer',
                                         model_name='magento.product.product')
                updater.run(variant.external_id, force=True, binding_template_id=binding)

        for template_delete in templates_delete:
            templates_delete[template_delete].unlink()
        self._update_price(binding, price)
        # Do also import translations
        translation_importer = self.component(
            usage='translation.importer',
        )
        translation_importer.run(
            self.external_id,
            binding,
            mapper='magento.product.template.import.mapper'
        )
        # Do import stock item
        stock_importer = self.component(usage='record.importer',
                                        model_name='magento.stock.item')
        stock_importer.run(self.magento_record['extension_attributes']['stock_item'])

    def _is_uptodate(self, binding):
        # TODO: Remove for production - only to test the update
        return False

    def _get_binding(self):
        binding = super(ProductTemplateImporter, self)._get_binding()
        if not binding:
            # Do search using the magento_id - maybe the sku did changed !
            binding = self.env['magento.product.template'].search([
                ('backend_id', '=', self.backend_record.id),
                ('magento_id', '=', self.magento_record['id']),
            ])
            # if we found binding here - then the update will also update the external_id on the binding record
        return binding

    def _import_stock_warehouse(self):
        record = self.magento_record
        stock_item = record['extension_attributes']['stock_item']
        binder = self.binder_for('magento.stock.warehouse')
        mwarehouse = binder.to_internal(stock_item['stock_id'])
        if not mwarehouse:
            # We do create the warehouse binding directly here - did not found a mapping on magento api
            # We do create the warehouse binding directly here - did not found a mapping on magento api
            binding = self.env['magento.stock.warehouse'].create({
                'backend_id': self.backend_record.id,
                'external_id': stock_item['stock_id'],
                'odoo_id': self.env['stock.warehouse'].search([('company_id', '=', self.backend_record.company_id.id)], limit=1).id,
            })
            self.backend_record.add_checkpoint(binding)

    def _import_dependencies(self):
        record = self.magento_record
        # Import attribute deps
        for attribute in record.get('custom_attributes'):
            # We do search binding using attribute_code - default is attribute_id !
            self._import_dependency(attribute['attribute_code'],
                                    'magento.product.attribute', external_field='attribute_code')
        # TODO: Check for product categorie dependency here !

        # Check for attributes in configurable - with values
        product_options = record['extension_attributes']['configurable_product_options']
        attribute_binder = self.binder_for('magento.product.attribute')
        attribute_value_binder = self.binder_for('magento.product.attribute.value')
        for product_option in product_options:
            attribute = attribute_binder.to_internal(product_option['attribute_id'], unwrap=True)
            if not attribute:
                # Do import the attribute
                self._import_dependency(product_option['attribute_id'], 'magento.product.attribute')
                attribute = attribute_binder.to_internal(product_option['attribute_id'], unwrap=True)
            # This is a configurable product option attribute - so set the create_variant flag
            if not attribute.create_variant:
                attribute.with_context(connector_no_export=True).create_variant = True
            # Check for attribute values
            for option_value in product_option['values']:
                attribute_value = attribute_value_binder.to_internal("%s_%s" % (product_option['attribute_id'], option_value['value_index']), unwrap=True)
                if not attribute_value:
                    # Do update the attribute - so the value will get added
                    self._import_dependency(product_option['attribute_id'], 'magento.product.attribute', always=True)
        self._import_stock_warehouse()


class ProductTemplateImportMapper(Component):
    _name = 'magento.product.template.import.mapper'
    _inherit = 'magento.product.product.import.mapper'
    _apply_on = ['magento.product.template']

    children = []


    @mapping
    def custom_values(self, record):
        """
        Force the custom attributes to be in the dictionnary
        so that creation of the template will get the custom values
        """
        custom_values = record['custom_attributes']
        return {'custom_attributes': custom_values}

    @mapping
    def attributes(self, record):
        '''
        We do overwrite the attributes function from product.product
        [
          {
            u'product_id': 2039,
            u'attribute_id': u'93',
            u'label': u'Color',
            u'values': [
              {
                u'value_index': 53
              },
              {
                u'value_index': 57
              },
              {
                u'value_index': 58
              }
            ],
            u'position': 1,
            u'id': 295
          },
          {
            u'product_id': 2039,
            u'attribute_id': u'145',
            u'label': u'Size',
            u'values': [
              {
                u'value_index': 172
              },
              {
                u'value_index': 173
              },
              {
                u'value_index': 174
              },
              {
                u'value_index': 175
              },
              {
                u'value_index': 176
              }
            ],
            u'position': 0,
            u'id': 294
          }
        ]
        :param record:
        :return:
        '''
        attribute_binder = self.binder_for('magento.product.attribute')
        line_binder = self.binder_for('magento.template.attribute.line')
        product_options = record['extension_attributes']['configurable_product_options']
        linemapper = self.component(usage='import.mapper', model_name='magento.template.attribute.line')
        odoo_options = []
        for product_option in product_options:
            # Check if it does already exists
            # Get internal attribute
            attribute = attribute_binder.to_internal(product_option['attribute_id'], unwrap=True)
            if not attribute:
                raise MappingError("The product attribute with "
                                   "magento id %s is not imported." %
                                   product_option['attribute_id'])
            line = line_binder.to_internal(product_option['id'], unwrap=False)
            map_record = linemapper.map_record(product_option, parent=record)
            if not line:
                # Create line
                odoo_options.append((0, 0, map_record.values(for_create=True)))
            else:
                # Update line
                odoo_options.append((1, line.id, map_record.values(for_create=False)))
        return {'magento_template_attribute_line_ids': odoo_options}

    @mapping
    def categories(self, record):
        # No categories on configurable product
        if not 'category_links' in record['extension_attributes']:
            return
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
    def auto_create_variants(self, records):
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
        product = self.env['product.template'].search(
            [('default_code', '=', record['sku'])], limit=1)
        if product:
            return {'odoo_id': product.product_tmpl_id.id}
        return {'magento_default_code': record['sku'],
                'default_code': record['sku']}

    @mapping
    def odoo_type(self, record):
        return {'type': 'product'}

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



