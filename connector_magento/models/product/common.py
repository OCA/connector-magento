# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import math
import xmlrpc.client

from collections import defaultdict

from odoo import models, fields, api
from odoo.addons.connector.exception import IDMissingInBackend
from odoo.addons.component.core import Component
from odoo.addons.component_event import skip_if
from odoo.addons.queue_job.job import job, related_action
from ...components.backend_adapter import MAGENTO_DATETIME_FORMAT

_logger = logging.getLogger(__name__)

PAGE_SIZE = 100


def chunks(items, length):
    for index in range(0, len(items), length):
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
            ('giftcard', 'Giftcard'),
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

    visibility = fields.Selection(
        selection=[('1', 'Not Visible Individually'),
                   ('2', 'Catalog'),
                   ('3', 'Search'),
                   ('4', 'Catalog, Search'),
                   ],
        string='Visibility',
        default='4',
        required=True,
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
        backends = defaultdict(set)
        for product in self:
            backends[product.backend_id].add(product.id)

        for backend, product_ids in list(backends.items()):
            self._recompute_magento_qty_backend(backend,
                                                self.browse(product_ids))
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

        location = self.env['stock.location']
        if self.env.context.get('location'):
            location = location.browse(self.env.context['location'])
        else:
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
    _magento2_model = 'products'
    _magento2_search = 'products'
    _magento2_key = 'sku'
    _admin_path = '/{model}/edit/id/{id}'

    def _call(self, method, arguments, http_method=None, storeview=None):
        try:
            return super(ProductProductAdapter, self)._call(method, arguments, http_method=http_method, storeview=storeview)
        except xmlrpc.client.Fault as err:
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
        if self.collection.version == '2.0':
            key = self._magento2_key or 'id'
            params = {}
            if self._magento2_search:
                params['fields'] = 'items[%s]' % key
                params.update(self.get_searchCriteria(filters))
            else:
                params['fields'] = key
                if filters:
                    raise NotImplementedError  # Unexpected much?
            items_ids = set()
            stop_searching = False
            current_page = 0
            params['fields'] = params['fields'] + ',total_count'

            while not stop_searching:
                current_page += 1
                params['searchCriteria[pageSize]'] = PAGE_SIZE
                params['searchCriteria[currentPage]'] = current_page
                params['searchCriteria[sortOrders][0][field]'] = 'id'
                params['searchCriteria[sortOrders][0][direction]'] = 'ASC'
                res = self._call(
                    self._magento2_search or self._magento2_model,
                    params)
                total_count = res.get('total_count')
                _logger.debug(
                    'Retrieved page {current_page} of {estimated_pages} '
                    'estimated pages for a total of {total_count} products'.
                    format(
                        current_page=current_page,
                        estimated_pages=math.ceil(total_count / PAGE_SIZE),
                        total_count=total_count))
                if 'items' in res:
                    res = res['items'] or []
                page_items = set(item[key] for item in res if item[key] != 0)
                if (len(items_ids) + len(page_items)) >= total_count or \
                        any(item in items_ids for item in page_items):
                    # As Magento would keep sending us the last products, stop
                    #  when it send any duplicate
                    stop_searching = True
                items_ids.update(page_items)
            return list(items_ids)

        # TODO add a search entry point on the Magento API
        return [int(row['product_id']) for row
                in self._call('%s.list' % self._magento_model,
                              [filters] if filters else [{}])]

    def read(self, id, storeview_id=None, attributes=None):
        """ Returns the information of a record

        :rtype: dict
        """
        if self.collection.version == '2.0':
            # TODO: storeview context in Magento 2.0
            res = super(ProductProductAdapter, self).read(
                id, attributes=attributes)
            if res:
                for attr in res.get('custom_attributes', []):
                    res[attr['attribute_code']] = attr['value']
            return res
        return self._call('ol_catalog_product.info',
                          [int(id), storeview_id, attributes, 'id'])

    def write(self, id, data, storeview_id=None):
        """ Update records on the external system """
        # XXX actually only ol_catalog_product.update works
        # the PHP connector maybe breaks the catalog_product.update
        if self.collection.version == '2.0':
            return self._call(
                'products/%s' % id, arguments={
                    'product': data
                },
                http_method='put',
                storeview='all',
            )
        return self._call('ol_catalog_product.update',
                          [int(id), data, storeview_id, 'id'])

    def get_images(self, id, storeview_id=None, data=None):
        if self.collection.version == '2.0':
            assert data
            return (entry for entry in
                    data.get('media_gallery_entries', [])
                    if entry['media_type'] == 'image')
        return self._call('product_media.list', [int(id), storeview_id, 'id'])

    def read_image(self, id, image_name, storeview_id=None):
        if self.collection.version == '2.0':
            raise NotImplementedError  # TODO
        return self._call('product_media.info',
                          [int(id), image_name, storeview_id, 'id'])

    def update_inventory(self, id, data):
        # product_stock.update is too slow
        if self.collection.version == '2.0':
            return self._call('products/%s/stockItems/1' % id, {"stockItem": data}, http_method='put')
        return self._call('oerp_cataloginventory_stock_item.update',
                          [int(id), data])


class MagentoBindingProductListener(Component):
    _name = 'magento.binding.product.product.listener'
    _inherit = 'base.connector.listener'
    _apply_on = ['magento.product.product']

    # fields which should not trigger an export of the products
    # but an export of their inventory
    INVENTORY_FIELDS = ('manage_stock',
                        'backorders',
                        'magento_qty',
                        )

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
