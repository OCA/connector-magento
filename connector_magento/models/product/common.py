# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import xmlrpclib

from collections import defaultdict

from odoo import models, fields, api
from odoo.addons.connector.exception import IDMissingInBackend
from odoo.addons.component.core import Component
from odoo.addons.component_event import skip_if
from odoo.addons.queue_job.job import job, related_action
from ...components.backend_adapter import MAGENTO_DATETIME_FORMAT
import odoo.addons.decimal_precision as dp


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
            ('giftcard', 'Giftcard')
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
    magento_id = fields.Integer('Magento ID')
    magento_configurable_id = fields.Many2one(comodel_name='magento.product.template',
                                              string='Configurable',
                                              required=False,
                                              ondelete='restrict',
                                              readonly=True)
    magento_name = fields.Char('Name', translate=True)
    magento_price = fields.Float('Backend Preis', default=0.0, digits=dp.get_precision('Product Price'),)
    magento_stock_item_ids = fields.One2many(
        comodel_name='magento.stock.item',
        inverse_name='magento_product_binding_id',
        string="Magento Stock Items",
    )


    @api.multi
    def sync_from_magento(self):
        self.ensure_one()
        with self.backend_id.work_on(self._name) as work:
            importer = work.component(usage='record.importer')
            return importer.run(self.external_id, force=True)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    magento_bind_ids = fields.One2many(
        comodel_name='magento.product.product',
        inverse_name='odoo_id',
        string='Magento Bindings',
    )

    @api.multi
    def write(self, vals):
        return super(ProductProduct, self).write(vals)


class ProductProductAdapter(Component):
    _name = 'magento.product.product.adapter'
    _inherit = 'magento.adapter'
    _apply_on = 'magento.product.product'
    

    _magento_model = 'catalog_product'
    _magento2_model = 'products'
    _magento2_search = 'products'
    _magento2_key = 'sku'
    _admin_path = '/{model}/edit/id/{id}'

    def _call(self, method, arguments, http_method=None, storeview=None):
        try:
            return super(ProductProductAdapter, self)._call(
                method, 
                arguments, 
                http_method=http_method, 
                storeview=storeview)
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
        if self.work.magento_api._location.version == '2.0':
            return super(ProductProductAdapter, self).search(filters=filters)
        # TODO add a search entry point on the Magento API
        return [int(row['product_id']) for row
                in self._call('%s.list' % self._magento_model,
                              [filters] if filters else [{}])]

    def read(self, id, storeview_code=None, attributes=None):
        """ Returns the information of a record

        :rtype: dict
        """
        if self.work.magento_api._location.version == '2.0':
            # TODO: storeview_code context in Magento 2.0
            res = super(ProductProductAdapter, self).read(
                id, attributes=attributes, storeview_code=storeview_code)
            if res:
                for attr in res.get('custom_attributes', []):
                    res[attr['attribute_code']] = attr['value']
            return res
        return self._call('ol_catalog_product.info',
                          [int(id), storeview_code, attributes, 'id'])

    def get_images(self, id, storeview_id=None, data=None):
        if self.work.magento_api._location.version == '2.0':
            assert data
            return (entry for entry in
                    data.get('media_gallery_entries', [])
                    if entry['media_type'] == 'image')
        else:
            return self._call('product_media.list', [int(id), storeview_id, 'id'])

    def read_image(self, id, image_name, storeview_id=None):
        if self.work.magento_api._location.version == '2.0':
            raise NotImplementedError  # TODO
        return self._call('product_media.info',
                          [int(id), image_name, storeview_id, 'id'])


class MagentoBindingProductListener(Component):
    _name = 'magento.binding.product.product.listener'
    _inherit = 'base.connector.listener'
    _apply_on = ['magento.product.product']

    # fields which should not trigger an export of the products
    # but an export of their inventory
    INVENTORY_FIELDS = ()

    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    def on_record_write(self, record, fields=None):
        if record.no_stock_sync:
            return
        inventory_fields = list(
            set(fields).intersection(self.INVENTORY_FIELDS)
        )
        if inventory_fields:
            record.with_delay(priority=20).export_inventory(
                fields=inventory_fields
            )


class MagentoProductVariantModelBinder(Component):
    """ Bind records and give odoo/magento ids correspondence

    Binding models are models called ``magento.{normal_model}``,
    like ``magento.res.partner`` or ``magento.product.product``.
    They are ``_inherits`` of the normal models and contains
    the Magento ID, the ID of the Magento Backend and the additional
    fields belonging to the Magento instance.
    """
    _name = 'magento.product.variant.binder'
    _inherit = 'magento.binder'
    _apply_on = ['magento.product.product']
