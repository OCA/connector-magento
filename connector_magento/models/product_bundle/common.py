# -*- coding: utf-8 -*-
# Copyright <YEAR(S)> <AUTHOR(S)>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from odoo import api, models, fields, _
from odoo.addons.component.core import Component
from ...components.backend_adapter import MAGENTO_DATETIME_FORMAT
import urllib
import odoo.addons.decimal_precision as dp


_logger = logging.getLogger(__name__)
'''
{
        "bundle_product_options": [
            {
                "option_id": 26,
                "title": "choice jacket",
                "required": true,
                "type": "select",
                "position": 1,
                "sku": "GA990-06",
                "product_links": [
                    {
                        "id": "222",
                        "sku": "GA2208",
                        "option_id": 26,
                        "qty": 1,
                        "position": 2,
                        "is_default": false,
                        "price": 0,
                        "price_type": 0,
                        "can_change_quantity": 0
                    },
                    {
                        "id": "223",
                        "sku": "GA2209",
                        "option_id": 26,
                        "qty": 1,
                        "position": 3,
                        "is_default": false,
                        "price": 0,
                        "price_type": 0,
                        "can_change_quantity": 0
                    },
                    {
                        "id": "224",
                        "sku": "GA2210",
                        "option_id": 26,
                        "qty": 1,
                        "position": 4,
                        "is_default": false,
                        "price": 0,
                        "price_type": 0,
                        "can_change_quantity": 0
                    },
                    {
                        "id": "225",
                        "sku": "GA2211",
                        "option_id": 26,
                        "qty": 1,
                        "position": 5,
                        "is_default": false,
                        "price": 0,
                        "price_type": 0,
                        "can_change_quantity": 0
                    },
                    {
                        "id": "226",
                        "sku": "GA2212",
                        "option_id": 26,
                        "qty": 1,
                        "position": 6,
                        "is_default": false,
                        "price": 0,
                        "price_type": 0,
                        "can_change_quantity": 0
                    },
                    {
                        "id": "227",
                        "sku": "GA2320",
                        "option_id": 26,
                        "qty": 1,
                        "position": 7,
                        "is_default": false,
                        "price": 0,
                        "price_type": 0,
                        "can_change_quantity": 0
                    }
                ]
            },
            {
                "option_id": 27,
                "title": "choice pants",
                "required": true,
                "type": "select",
                "position": 2,
                "sku": "GA990-06",
                "product_links": [
                    {
                        "id": "228",
                        "sku": "GA2221",
                        "option_id": 27,
                        "qty": 1,
                        "position": 1,
                        "is_default": false,
                        "price": 0,
                        "price_type": 0,
                        "can_change_quantity": 0
                    },
                    {
                        "id": "229",
                        "sku": "GA2222",
                        "option_id": 27,
                        "qty": 1,
                        "position": 2,
                        "is_default": false,
                        "price": 0,
                        "price_type": 0,
                        "can_change_quantity": 0
                    },
                    {
                        "id": "230",
                        "sku": "GA2223",
                        "option_id": 27,
                        "qty": 1,
                        "position": 3,
                        "is_default": false,
                        "price": 0,
                        "price_type": 0,
                        "can_change_quantity": 0
                    },
                    {
                        "id": "231",
                        "sku": "GA2224",
                        "option_id": 27,
                        "qty": 1,
                        "position": 4,
                        "is_default": false,
                        "price": 0,
                        "price_type": 0,
                        "can_change_quantity": 0
                    },
                    {
                        "id": "232",
                        "sku": "GA2225",
                        "option_id": 27,
                        "qty": 1,
                        "position": 5,
                        "is_default": false,
                        "price": 0,
                        "price_type": 0,
                        "can_change_quantity": 0
                    },
                    {
                        "id": "233",
                        "sku": "GA2226",
                        "option_id": 27,
                        "qty": 1,
                        "position": 6,
                        "is_default": false,
                        "price": 0,
                        "price_type": 0,
                        "can_change_quantity": 0
                    },
                    {
                        "id": "234",
                        "sku": "GA2330",
                        "option_id": 27,
                        "qty": 1,
                        "position": 7,
                        "is_default": false,
                        "price": 0,
                        "price_type": 0,
                        "can_change_quantity": 0
                    }
                ]
            },
            {
                "option_id": 54,
                "title": "FREE detergent to a set",
                "required": true,
                "type": "radio",
                "position": 3,
                "sku": "GA990-06",
                "product_links": [
                    {
                        "id": "367",
                        "sku": "NW181P01",
                        "option_id": 54,
                        "qty": 1,
                        "position": 1,
                        "is_default": false,
                        "price": 0,
                        "price_type": 0,
                        "can_change_quantity": 0
                    }
                ]
            },
            {
                "option_id": 55,
                "title": "FREE waterproofening spray to a set",
                "required": true,
                "type": "radio",
                "position": 4,
                "sku": "GA990-06",
                "product_links": [
                    {
                        "id": "368",
                        "sku": "NW571P01",
                        "option_id": 55,
                        "qty": 1,
                        "position": 1,
                        "is_default": false,
                        "price": 0,
                        "price_type": 0,
                        "can_change_quantity": 0
                    }
                ]
            }
        ]
    },
    "product_links": [],
    "options": [],
  }
'''

class MagentoProductBundle(models.Model):
    _name = 'magento.product.bundle'
    _inherit = 'magento.binding'
    _inherits = {'product.product': 'odoo_id'}
    _description = 'Magento Product Bundle'

    attribute_set_id = fields.Many2one('magento.product.attributes.set',
                                       string='Attribute set')

    odoo_id = fields.Many2one(comodel_name='product.product',
                              string='Product',
                              required=True,
                              ondelete='restrict')
    bundle_option_ids = fields.One2many('magento.bundle.option', 'magento_bundle_id', string='Options')

    # XXX website_ids can be computed from categories
    website_ids = fields.Many2many(comodel_name='magento.website',
                                   string='Websites',
                                   readonly=True)

    product_type = fields.Char()
    magento_id = fields.Integer('Magento ID')
    magento_name = fields.Char('Name', translate=True)
    magento_price = fields.Float('Backend Preis', default=0.0, digits=dp.get_precision('Product Price'),)
    created_at = fields.Date('Created At (on Magento)')
    updated_at = fields.Date('Updated At (on Magento)')


    @api.multi
    def sync_from_magento(self):
        self.ensure_one()
        with self.backend_id.work_on(self._name) as work:
            importer = work.component(usage='record.importer')
            return importer.run(self.external_id, force=True)

    @api.model
    def create(self, vals):
        return super(MagentoProductBundle, self).create(vals)

'''
                "option_id": 26,
                "title": "choice jacket",
                "required": true,
                "type": "select",
                "position": 1,
                "sku": "GA990-06",
                "product_links": [

'''
class MagentoBundleOption(models.Model):
    _name = 'magento.bundle.option'
    _inherit = 'magento.binding'
    _description = 'Magento Bundle Option'

    title = fields.Char('Title')
    required = fields.Boolean('Required')
    type = fields.Selection([
        ('select', 'Select'),
        ('radio', 'Radio'),
    ], default='select', string="Type")
    position = fields.Integer('Position')
    magento_bundle_id = fields.Many2one(comodel_name='magento.product.bundle',
                                        string="Magento Bundle",
                                        required=True)
    option_product_ids = fields.One2many('magento.bundle.option.product',
                                         'magento_bundle_option_id',
                                         string='Products')

'''
                    {
                        "id": "222",
                        "sku": "GA2208",
                        "option_id": 26,
                        "qty": 1,
                        "position": 2,
                        "is_default": false,
                        "price": 0,
                        "price_type": 0,
                        "can_change_quantity": 0
                    },

'''
class MagentoBundleOptionProduct(models.Model):
    _name = 'magento.bundle.option.product'
    _inherit = 'magento.binding'
    _description = 'Magento Bundle Option Product'

    magento_product_id = fields.Many2one(comodel_name='magento.product.product',
                                         required=True,
                                         string="Magento Product")
    magento_bundle_option_id = fields.Many2one(comodel_name='magento.bundle.option',
                                               required=True,
                                               string="Magento Bundle Option")

    qty = fields.Integer('Quantity')
    position = fields.Integer('Position')
    is_default = fields.Boolean('Is Default')
    price = fields.Float('Price')
    price_type = fields.Integer('Price Type')
    can_change_quantity = fields.Integer('Can change quantity')


class ProductProduct(models.Model):
    _inherit = 'product.product'

    magento_bundle_bind_ids = fields.One2many(
        comodel_name='magento.product.bundle',
        inverse_name='odoo_id',
        string='Magento Bundle Bindings',
    )

    @api.multi
    def _need_procurement(self):
        # Bundle product does not need procurment
        for product in self:
            if product.type == 'bundle':
                return False
        return super(ProductProduct, self)._need_procurement()


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    type = fields.Selection(selection_add=[('bundle', _(u'Bundle'))])


class ProductBundleAdapter(Component):
    _name = 'magento.product.bundle.adapter'
    _inherit = 'magento.adapter'
    _apply_on = 'magento.product.bundle'

    _magento_model = 'catalog_product'
    _magento2_model = 'products'
    _magento2_search = 'products'
    _magento2_key = 'sku'
    _admin_path = '/{model}/edit/id/{id}'

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
        filters.setdefault('type_id', {})
        filters['type_id']['eq'] = 'bundle'
        if self.work.magento_api._location.version == '2.0':
            return super(ProductBundleAdapter, self).search(filters=filters)
        # TODO add a search entry point on the Magento API
        return [int(row['product_id']) for row
                in self._call('%s.list' % self._magento_model,
                              [filters] if filters else [{}])]

    def create(self, data):
        """ Create a record on the external system """
        if self.work.magento_api._location.version == '2.0':
            new_product = super(ProductBundleAdapter, self)._call(
                'products', {
                    'product': data
                },
                http_method='post')
            return new_product['id']

    def list_variants(self, sku):
        def escape(term):
            if isinstance(term, basestring):
                return urllib.quote(term.encode('utf-8'), safe='')
            return term

        if self.work.magento_api._location.version == '2.0':
            res = self._call('configurable-products/%s/children' % (escape(sku)), None)
            return res

    def write(self, id, data, storeview_id=None):
        """ Update records on the external system """
        # XXX actually only ol_catalog_product.update works
        # the PHP connector maybe breaks the catalog_product.update
        if self.work.magento_api._location.version == '2.0':
            _logger.info("Prepare to call api with %s " % data)
            # Replace by the
            id = data['sku']
            super(ProductBundleAdapter, self)._call(
                'products/%s' % id, {
                    'product': data
                },
                http_method='put')

            stock_datas = {"stockItem": {
                'is_in_stock': True}}
            return super(ProductBundleAdapter, self)._call(
                'products/%s/stockItems/1' % id,
                stock_datas,
                http_method='put')
        #             raise NotImplementedError  # TODO
        return self._call('ol_catalog_product.update',
                          [int(id), data, storeview_id, 'id'])

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
