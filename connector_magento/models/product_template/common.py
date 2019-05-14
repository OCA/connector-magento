# -*- coding: utf-8 -*-
# Copyright 2019 Callino
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from odoo import api, models, fields
from odoo.addons.component.core import Component
from odoo.addons.queue_job.job import job, related_action
from ...components.backend_adapter import MAGENTO_DATETIME_FORMAT
import urllib
import odoo.addons.decimal_precision as dp
from urlparse import urljoin


_logger = logging.getLogger(__name__)


class MagentoProductTemplate(models.Model):
    _name = 'magento.product.template'
    _inherit = 'magento.binding'
    _inherits = {'product.template': 'odoo_id'}
    _description = 'Magento Product Template'
    _magento_backend_path = 'catalog/product/edit/id'
    _magento_frontend_path = 'catalog/product/view/id'

    @api.depends('backend_id', 'external_id')
    def _compute_magento_backend_url(self):
        for binding in self:
            if binding._magento_backend_path:
                binding.magento_backend_url = "%s/%s" % (urljoin(binding.backend_id.admin_location, binding._magento_backend_path), binding.magento_id)
            if binding._magento_frontend_path:
                binding.magento_frontend_url = "%s/%s" % (urljoin(binding.backend_id.location, binding._magento_frontend_path), binding.magento_id)

    @api.model
    def product_type_get(self):
        return [
            ('simple', 'Simple Product'),
            ('configurable', 'Configurable Product'),
            ('bundle', 'Bundle Product'),
            ]       
    
    attribute_set_id = fields.Many2one('magento.product.attributes.set',
                                       string='Attribute set')

    odoo_id = fields.Many2one(comodel_name='product.template',
                              string='Product Template',
                              required=True,
                              ondelete='restrict')
    # XXX website_ids can be computed from categories
    website_ids = fields.Many2many(comodel_name='magento.website',
                                   string='Websites',
                                   readonly=True)

#     product_type = fields.Char()
    product_type = fields.Selection(selection='product_type_get',
                                    string='Magento Product Type',
                                    default='simple',
                                    required=True)
    
    magento_id = fields.Integer('Magento ID')
    magento_name = fields.Char('Name', translate=True)
    magento_price = fields.Float('Backend Preis', default=0.0, digits=dp.get_precision('Product Price'),)
    created_at = fields.Date('Created At (on Magento)')
    updated_at = fields.Date('Updated At (on Magento)')
    magento_product_ids = fields.One2many(comodel_name='magento.product.product',
                                          inverse_name='magento_configurable_id',
                                          string='Variants',
                                          readonly=True)

    magento_template_attribute_line_ids = fields.One2many(
        comodel_name='magento.template.attribute.line',
        inverse_name='magento_template_id',
        string='Magento Attribute lines for templates',
    )

    _sql_constraints = [
        ('backend_magento_id_uniqueid',
         'UNIQUE (backend_id, magento_id)',
         'Duplicate binding of product detected, maybe SKU changed ?')]

    @api.multi
    @job(default_channel='root.magento')
    def sync_from_magento(self):
        for binding in self:
            binding.with_delay().run_sync_from_magento()

    @api.multi
    @job(default_channel='root.magento')
    def run_sync_from_magento(self):
        self.ensure_one()
        with self.backend_id.work_on(self._name) as work:
            importer = work.component(usage='record.importer')
            return importer.run(self.external_id, force=True)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    magento_template_bind_ids = fields.One2many(
        comodel_name='magento.product.template',
        inverse_name='odoo_id',
        string='Magento Template Bindings',
    )
    magento_bind_ids = fields.One2many(
        comodel_name='magento.product.product',
        inverse_name='odoo_id',
        string='Magento Bindings',
    )
    auto_create_variants = fields.Boolean('Auto Create Variants', default=True)
    magento_default_code = fields.Char(string="Default code used for magento")

    @api.model
    def create(self, vals):
        # Avoid to create variants
        if vals.get('auto_create_variants', True):
            # If auto create is true - then create the normal way
            return super(ProductTemplate, self).create(vals)
        # Else avoid creating the variants
        me = self.with_context(create_product_product=True)
        
        tpl = super(ProductTemplate, me).create(vals)    
        for prod in tpl.magento_template_bind_ids:
                if prod.product_variant_count > 1 :
                    self.env['magento.template.attribute.line']._update_attribute_lines(prod)
        return tpl 

    @api.multi
    def create_variant_ids(self):
        if self.env.context.get('create_product_product', False):
            # Do not try to create / update variants
            return True
        return super(ProductTemplate, self).create_variant_ids()

    @api.multi
    def write(self, vals):
        for tpl in self:
            if vals.get('auto_create_variants', tpl.auto_create_variants):
                # do auto create variants
                me = tpl
            else:
                # do not auto create variants
                me = tpl.with_context(create_product_product=True)
            res = super(ProductTemplate, me).write(vals)
        return res


class ProductTemplateAdapter(Component):
    _name = 'magento.product.template.adapter'
    _inherit = 'magento.adapter'
    _apply_on = 'magento.product.template'

    _magento_model = 'catalog_product'
    _magento2_model = 'products'
    _magento2_search = 'products'
    _magento2_name = 'product'
    _magento2_key = 'sku'
    _admin_path = '/{model}/edit/id/{id}'

    def _get_id_from_create(self, result, data=None):
        return data[self._magento2_key]

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
        filters['type_id']['eq'] = 'configurable'
        if self.work.magento_api._location.version == '2.0':
            return super(ProductTemplateAdapter, self).search(filters=filters)
        # TODO add a search entry point on the Magento API
        return [int(row['product_id']) for row
                in self._call('%s.list' % self._magento_model,
                              [filters] if filters else [{}])]

    def list_variants(self, sku):
        def escape(term):
            if isinstance(term, basestring):
                return urllib.quote(term.encode('utf-8'), safe='')
            return term

        if self.work.magento_api._location.version == '2.0':
            res = self._call('configurable-products/%s/children' % (escape(sku)), None)
            return res

    def write(self, id, data, binding=None):
        """ Update records on the external system """
        storeview_id = self.work.storeview_id if hasattr(self.work, 'storeview_id') else False
        if self.work.magento_api._location.version == '2.0':
            _logger.info("Prepare to call api with %s " % data)
            # Replace by the
            id = data['sku']
            storeview_code = storeview_id.code if storeview_id else False
            super(ProductTemplateAdapter, self)._call(
                'products/%s' % id, {
                    'product': data
                },
                http_method='put', storeview=storeview_code)

            stock_datas = {"stockItem": {
                'is_in_stock': True}}
            return super(ProductTemplateAdapter, self)._call(
                'products/%s/stockItems/1' % id,
                stock_datas,
                http_method='put', )
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
