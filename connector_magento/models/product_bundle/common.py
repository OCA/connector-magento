# -*- coding: utf-8 -*-
# Copyright 2019 Callino
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from odoo import api, models, fields, _
from odoo.addons.component.core import Component
from ...components.backend_adapter import MAGENTO_DATETIME_FORMAT
import urllib.request, urllib.parse, urllib.error
import odoo.addons.decimal_precision as dp
from urllib.parse import urljoin
from odoo.addons.queue_job.job import job
from odoo.addons.queue_job.job import identity_exact

_logger = logging.getLogger(__name__)


class MagentoProductBundle(models.Model):
    _name = 'magento.product.bundle'
    _inherit = 'magento.binding'
    _inherits = {'product.product': 'odoo_id'}
    _description = 'Magento Product Bundle'
    _magento_backend_path = 'catalog/product/edit/id'
    _magento_frontend_path = 'catalog/product/view/id'

    @api.depends('backend_id', 'external_id')
    def _compute_magento_backend_url(self):
        for binding in self:
            if binding._magento_backend_path:
                binding.magento_backend_url = "%s/%s" % (urljoin(binding.backend_id.admin_location, binding._magento_backend_path), binding.magento_id)
            if binding._magento_frontend_path:
                binding.magento_frontend_url = "%s/%s" % (urljoin(binding.backend_id.location, binding._magento_frontend_path), binding.magento_id)

    @api.depends('backend_id', 'odoo_id')
    def _compute_product_categories(self):
        for binding in self:
            magento_product_position_ids = self.env['magento.product.position'].search([
                ('magento_product_category_id.backend_id', '=', binding.backend_id.id),
                ('product_template_id', '=', binding.odoo_id.product_tmpls_id.id),
            ])
            binding.magento_product_category_ids = [mpp.magento_product_category_id.id for mpp in magento_product_position_ids]
            binding.magento_product_position_ids = magento_product_position_ids

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
    magento_product_position_ids = fields.One2many(
        comodel_name='magento.product.position',
        compute='_compute_product_categories',
        string='Product positions'
    )
    magento_product_category_ids = fields.One2many(
        comodel_name='magento.product.category',
        compute='_compute_product_categories',
        string='Product categories'
    )
    _sql_constraints = [
        ('backend_magento_id_uniqueid',
         'UNIQUE (backend_id, magento_id)',
         'Duplicate binding of product detected, maybe SKU changed ?')]


    @api.multi
    @job(default_channel='root.magento')
    def sync_from_magento(self):
        for binding in self:
            binding.with_delay(identity_key=identity_exact).run_sync_from_magento()

    @api.multi
    @job(default_channel='root.magento')
    def run_sync_from_magento(self):
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

    type = fields.Selection(selection_add=[('bundle', _('Bundle'))])


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
            if isinstance(term, str):
                return urllib.parse.quote(term.encode('utf-8'), safe='')
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
