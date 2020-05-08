# Copyright 2013-2019 Camptocamp SA
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import xmlrpc.client

from collections import defaultdict

from odoo import models, fields, api
from odoo.addons.connector.exception import IDMissingInBackend
from odoo.addons.component.core import Component
from odoo.addons.component_event import skip_if
from odoo.addons.queue_job.job import job, related_action
from odoo.exceptions import UserError
from odoo.tools.translate import _
from ...components.backend_adapter import MAGENTO_DATETIME_FORMAT

_logger = logging.getLogger(__name__)


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
            ('giftcard', 'Giftcard')
            # XXX activate when supported
            # ('grouped', 'Grouped Product'),
            # ('bundle', 'Bundle Product'),
        ]

    odoo_id = fields.Many2one(comodel_name='product.product',
                              string='Odoo Product',
                              required=True,
                              ondelete='restrict')
    magento_internal_id = fields.Char(
        help=(
            'In Magento2, we have to keep track of both the external_id (the '
            'product SKU) which is used in the Magento2 REST API, as well as '
            'the Magento internal id as used in the admin URL.'))
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

    @api.model
    def _get_admin_path(self, backend, external_id):
        """ In Magento2, we can only link to the product when we have already
        imported it """
        if backend.version == '1.7':
            return '/{model}/edit/id/{id}'
        magento_internal_id = self.search(
            [('backend_id', '=', backend.id),
             ('external_id', '=', external_id)],
            limit=1).magento_internal_id
        if magento_internal_id:
            return 'catalog/product/edit/id/%s' % magento_internal_id
        raise UserError(_(
            'We have to import the product before we can provide the admin '
            'link to it.'))


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
            return super(ProductProductAdapter, self)._call(
                method, arguments, http_method=http_method,
                storeview=storeview)
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
        if self.collection.version == '1.7':
            # TODO add a search entry point on the Magento API
            return [int(row['product_id']) for row
                    in self._call('%s.list' % self._magento_model,
                                  [filters] if filters else [{}])]
        return super(ProductProductAdapter, self).search(filters=filters)

    def read(self, external_id, storeview_id=None, attributes=None):
        """ Returns the information of a record

        :rtype: dict
        """
        # pylint: disable=method-required-super
        if self.collection.version == '1.7':
            return self._call(
                'ol_catalog_product.info',
                [int(external_id), storeview_id, attributes, 'id'])
        res = super(ProductProductAdapter, self).read(
            external_id, attributes=attributes, storeview=storeview_id)
        if res:
            for attr in res.get('custom_attributes', []):
                res[attr['attribute_code']] = attr['value']
        return res

    def write(self, external_id, data, storeview_id=None):
        """ Update records on the external system """
        # pylint: disable=method-required-super
        # XXX actually only ol_catalog_product.update works
        # the PHP connector maybe breaks the catalog_product.update
        if self.collection.version == '1.7':
            return self._call('ol_catalog_product.update',
                              [int(external_id), data, storeview_id, 'id'])
        raise NotImplementedError  # TODO

    def get_images(self, external_id, storeview_id=None, data=None):
        """ Fetch image metadata either by querying Magento 1.x, or extracting
        it from the product data for Magento 2.x """
        if self.collection.version == '1.7':
            return self._call('product_media.list',
                              [int(external_id), storeview_id, 'id'])

        res = []
        # Fetch base media url from storeview
        storeview = (
            self.env['magento.storeview'].browse(storeview_id) if storeview_id
            else self.env['magento.storeview'].search(
                [('backend_id', '=', self.collection.id),
                 ('code', '=', 'default')]))
        base_url = (storeview.base_media_url or
                    '%s/media/' % self.backend_record.location)

        for entry in data.get('media_gallery_entries', []):
            if entry['media_type'] == 'image':
                entry['url'] = '%scatalog/product/%s' % (
                    base_url, entry['file'])
                res.append(entry)
        return res

    def read_image(self, external_id, image_name, storeview_id=None):
        if self.collection.version == '1.7':
            return self._call(
                'product_media.info',
                [int(external_id), image_name, storeview_id, 'id'])
        raise NotImplementedError  # TODO

    def update_inventory(self, external_id, data):
        """ Update the default stock. For Magento2, first retrieve the stock
        item that applies to this stock for the product. """
        if self.collection.version == '1.7':
            # product_stock.update is too slow
            return self._call('oerp_cataloginventory_stock_item.update',
                              [int(external_id), data])

        # Magento2
        data = {'stockItem': data}
        res = self._call('stockItems/%s' % self.escape(external_id), None)
        if isinstance(res, dict):
            res = [res]
        item_id = 0
        for item in res:
            if item['stock_id'] == 1:
                item_id = item['item_id']
                break
        else:
            raise ValueError(
                'No stock item found for product %s for default stock_id 1' %
                external_id)
        self._call('products/%s/stockItems/%s' % (
            self.escape(external_id), item_id), data, http_method='put')


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
