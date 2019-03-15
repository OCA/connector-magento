# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging
import requests
import base64
import sys

from odoo import models, fields, api

from odoo import _
from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create
from odoo.addons.connector.exception import MappingError, InvalidDataError
from ...components.mapper import normalize_datetime

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
        external_ids = self.backend_adapter.search(filters,
                                                   from_date=from_date,
                                                   to_date=to_date)
        _logger.info('search for magento product templates %s returned %s',
                     filters, external_ids)
        for external_id in external_ids:
            self._import_record(external_id)


class ProductTemplateImporter(Component):
    _name = 'magento.product.template.importer'
    _inherit = 'magento.importer'
    _apply_on = ['magento.product.template']

    def _create(self, data):
        # create_product_product - Avoid creating variant products
        binding = super(ProductTemplateImporter, self)._create(data)
        self.backend_record.add_checkpoint(binding)
        return binding

    def _after_import(self, binding):
        pass

    def _is_uptodate(self, binding):
        # TODO: Remove for production - only to test the update
        return False

    def _import_dependencies(self):
        record = self.magento_record
        # TODO: Check for dependencies
        pass

class ProductTemplateImportMapper(Component):
    _name = 'magento.product.template.import.mapper'
    _inherit = 'magento.product.product.import.mapper'
    _apply_on = ['magento.product.template']

    children = []

    @mapping
    def attr_ids(self, record):
        '''
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
    def variants(self, record):
        # Variants are in extension_attributes.configurable_product_links
        configurable_product_links = record['extension_attributes']['configurable_product_links']
        binder = self.binder_for('magento.product.product')
        variant_ids = []
        for product_id in configurable_product_links:
            binder._external_field = 'magento_id'
            variant = binder.to_internal(product_id, unwrap=True)
            binder._external_field = 'external_id'
            if not variant:
                raise MappingError("The product variant with "
                                   "magento id %s is not imported." %
                                   product_id)

            variant_ids.append((4, variant.id))
        return {'product_variant_ids': variant_ids}

    @only_create
    @mapping
    def odoo_id(self, record):
        """ Will bind the product to an existing one with the same code """
        product = self.env['product.product'].search(
            [('default_code', '=', record['sku'])], limit=1)
        if product:
            return {'odoo_id': product.product_tmpl_id.id}

    @mapping
    def type(self, record):
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



