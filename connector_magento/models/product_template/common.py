# -*- coding: utf-8 -*-
# Copyright 2019 Callino
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import ast
from odoo import api, models, fields
from lxml import etree
from odoo.osv.orm import setup_modifiers
from odoo.addons.component.core import Component
from odoo.addons.queue_job.job import job, related_action
from ...components.backend_adapter import MAGENTO_DATETIME_FORMAT
import urllib
import odoo.addons.decimal_precision as dp
from odoo.addons.queue_job.job import identity_exact
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
#             ('virtual', 'Virtual Product'),
#             ('downloadable', 'Downloadable Product'),
#             ('giftcard', 'Giftcard'),
            # XXX activate when supported
            # ('grouped', 'Grouped Product'),
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

    magento_template_attribute_value_ids = fields.One2many(
        comodel_name='magento.custom.template.attribute.values',
        inverse_name='magento_product_template_id',
        string='Magento Simple Custom Attributes Values for templates',
    )

    @api.multi
    def sync_from_magento(self):
        self.ensure_one()
        with self.backend_id.work_on(self._name) as work:
            importer = work.component(usage='record.importer')
            return importer.run(self.external_id, force=True)

    @api.multi
    def sync_to_magento(self):
        self.ensure_one()
        #First export the datas from no storeviews !
        self.with_delay(priority=20,
                        identity_key=identity_exact
                        ).export_product_template()
        

    @job(default_channel='root.magento')
    @related_action(action='related_action_unwrap_binding')
    @api.multi
    def export_product_template(self, fields=None, storeview_id=None):
        """ Export the attributes configuration of a product. """
        self.ensure_one()
            # TODO make different usage
        
        with self.backend_id.work_on(
                self._name,
                storeview_id=storeview_id
                ) as work:
#                 exporter = work.with_context(
#                     storeview_id=storeview_id).component(usage='record.exporter')
                exporter = work.component(usage='record.exporter')
                return exporter.run(self)
                

    def action_magento_template_custom_attributes(self):
        action = self.env['ir.actions.act_window'].for_xml_id(
            'connector_magento_product_catalog',
            'action_magento_custom_template_attributes')

        action['domain'] = unicode([('magento_product_template_id', '=', self.id)])
        ctx = action.get('context', '{}') or '{}'

        action_context = ast.literal_eval(ctx)
        action_context.update({
            'default_attribute_set_id': self.attribute_set_id.id,
            'default_magento_product_template_id': self.id})
        #
        # #         action_context = ctx
        #         action_context.update({
        #             'default_project_id': self.project_id.id})
        action['context'] = action_context
        return action

    #         "
    #                                 type="object" string="Custom Values" class="oe_stat_button"
    #                                 context="{'search_default_magento_product_id': [active_id],
    #                             'default_attribute_set_id': attribute_set_id,
    #                             'default_magento_product_id': active_id, }"

    #     @job(default_channel='root.magento')
    #     @related_action(action='related_action_unwrap_binding')
    #     @api.multi
    #     def export_inventory(self, fields=None):
    #         """ Export the inventory configuration and quantity of a product. """
    #         self.ensure_one()
    #         with self.backend_id.work_on(self._name) as work:
    #             exporter = work.component(usage='product.inventory.exporter')
    #             return exporter.run(self, fields)
    #
    #     @api.multi
    #     def recompute_magento_qty(self):
    #         """ Check if the quantity in the stock location configured
    #         on the backend has changed since the last export.
    #
    #         If it has changed, write the updated quantity on `magento_qty`.
    #         The write on `magento_qty` will trigger an `on_record_write`
    #         event that will create an export job.
    #
    #         It groups the products by backend to avoid to read the backend
    #         informations for each product.
    #         """
    #         # group products by backend
    #         backends = defaultdict(set)
    #         for product in self:
    #             backends[product.backend_id].add(product.id)
    #
    #         for backend, product_ids in backends.iteritems():
    #             self._recompute_magento_qty_backend(backend,
    #                                                 self.browse(product_ids))
    #         return True
    #
    #     @api.multi
    #     def _recompute_magento_qty_backend(self, backend, products,
    #                                        read_fields=None):
    #         """ Recompute the products quantity for one backend.
    #
    #         If field names are passed in ``read_fields`` (as a list), they
    #         will be read in the product that is used in
    #         :meth:`~._magento_qty`.
    #
    #         """
    #         if backend.product_stock_field_id:
    #             stock_field = backend.product_stock_field_id.name
    #         else:
    #             stock_field = 'virtual_available'
    #
    #         location = self.env['stock.location']
    #         if self.env.context.get('location'):
    #             location = location.browse(self.env.context['location'])
    #         else:
    #             location = backend.warehouse_id.lot_stock_id
    #
    #         product_fields = ['magento_qty', stock_field]
    #         if read_fields:
    #             product_fields += read_fields
    #
    #
    #
    #         self_with_location = self.with_context(location=location.id)
    #         for chunk_ids in chunks(products.ids, self.RECOMPUTE_QTY_STEP):
    #             records = self_with_location.browse(chunk_ids)
    #             for product in records.read(fields=product_fields):
    #                 new_qty = self._magento_qty(product,
    #                                             backend,
    #                                             location,
    #                                             stock_field)
    #                 if new_qty != product['magento_qty']:
    #                     self.browse(product['id']).magento_qty = new_qty
    #
    #     @api.multi
    #     def _magento_qty(self, product, backend, location, stock_field):
    #         """ Return the current quantity for one product.
    #
    #         Can be inherited to change the way the quantity is computed,
    #         according to a backend / location.
    #
    #         If you need to read additional fields on the product, see the
    #         ``read_fields`` argument of :meth:`~._recompute_magento_qty_backend`
    #
    #         """
    #         return product[stock_field]

    @api.model
    def create(self, vals):
        mg_prod_id = super(MagentoProductTemplate, self).create(vals)
        org_vals = vals.copy()
        attributes = mg_prod_id.attribute_set_id.attribute_ids
        cstm_att_mdl = self.env['magento.custom.template.attribute.values']
        for att in attributes:
            vals = {
                #                 'backend_id': self.backend_id.id,
                'magento_product_template_id': mg_prod_id.id,
                'attribute_id': att.id,
                #                 'magento_attribute_type': att.frontend_input,
                #                 'product_template_id': self.odoo_id.id,
                #                 'odoo_field_name': att.odoo_field_name.id or False
            }
            cst_value = cstm_att_mdl.with_context(no_update=True).create(vals)
            if cst_value.odoo_field_name.id:
                mg_prod_id.check_field_mapping(
                    cst_value.odoo_field_name.name,
                    mg_prod_id[cst_value.odoo_field_name.name])
                
        if 'custom_attributes' in org_vals:
            magento_attr_mdl = self.env['magento.product.attribute']            
            for cst in org_vals['custom_attributes']:
                cst_value_id = mg_prod_id.magento_template_attribute_value_ids.filtered(
                    lambda v: v.attribute_id.attribute_code == cst['attribute_code'])
                if cst_value_id.odoo_field_name.id:
                    mg_prod_id.check_field_mapping(
                        cst_value_id.odoo_field_name.name, 
                        cst['value']
                        )
                elif cst_value_id.id:
                    cst_value_id.write({
                        'attribute_text': cst['value']})
            
#         if mg_prod_id.odoo_id.product_variant_count > 1 :
#             self.env['magento.template.attribute.line']._update_attribute_lines(mg_prod_id)
        
        return mg_prod_id

    @api.multi
    def check_field_mapping(self, field, vals):
        """
        # Check if the Odoo Field has a matching attribute in Magento
        # Update the value
        # Return an appropriate dictionnary
        :param field : field representation as ...
        :param vals : dictionnary of ... 
        
        :return : dictionnary
        """
        self.ensure_one()
        #         att_id = 0
        custom_model = self.env['magento.custom.template.attribute.values']
        odoo_fields = self.env['ir.model.fields'].search([
            ('name', '=', field),
            ('model', 'in', ['product.template'])])

        att_ids = self.env['magento.product.attribute'].search(
            [('odoo_field_name', 'in', [o.id for o in odoo_fields]),
             ('backend_id', '=', self.backend_id.id)
             ])

        if len(att_ids) > 0:
            att_id = att_ids[0]
            values = custom_model.search(
                [('magento_product_template_id', '=', self.id),
                 ('attribute_id', '=', att_id.id),
                  ('store_view_id', '=', False)
                 ])
            custom_vals = {
                'magento_product_template_id': self.id,
                'attribute_id': att_id.id,
                'attribute_text': self[field],
                'attribute_select': False,
                'attribute_multiselect': False,
            }
            odoo_field_type = odoo_fields[0].ttype
            if odoo_field_type in ['many2one', 'many2many'] \
                    and 'text' in att_id.frontend_input:
                custom_vals.update({
                    'attribute_text': str(
                        [v.magento_bind_ids.external_id for v in self[field]
                         ])})

            if att_id.frontend_input == 'boolean':
                custom_vals.update({
                    'attribute_text': str(int(self[field]))})
            if att_id.frontend_input == 'select':
                custom_vals.update({
                    'attribute_text': False,
                    'attribute_multiselect': False,
                    'attribute_select': self[field].magento_bind_ids[0].id})
            if att_id.frontend_input == 'multiselect':
                custom_vals.update({
                    'attribute_text': False,
                    'attribute_multiselect': False,
                    'attribute_multiselect':
                        [(6, False, [
                            v.id for v in self[field].magento_bind_ids])]})
            if len(values) == 0:
                custom_model.with_context(no_update=True).create(custom_vals)
            else:
                values.with_context(no_update=True).write(custom_vals)


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
        org_vals = vals.copy()

        for tpl in self:
            if vals.get('auto_create_variants', tpl.auto_create_variants):
                # do auto create variants
                me = tpl
            else:
                # do not auto create variants
                me = tpl.with_context(create_product_product=True)
            res = super(ProductTemplate, me).write(vals)
            # this part is for custom odoo fields to magento attributes
            for prod in tpl.magento_template_bind_ids:
                for key in org_vals:
                    prod.check_field_mapping(key, vals)
                    
                if prod.product_variant_count > 1 :
                    self.env['magento.template.attribute.line']._update_attribute_lines(prod)
        return res

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(ProductTemplate, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)

        if res['model'] in ['product.template', 'product.product'] and \
            res['type'] == 'form':
            doc = etree.XML(res['arch'])
            mapped_field_ids = self.env['magento.product.attribute'].search(
                [('odoo_field_name', '!=', False)]).mapped('odoo_field_name')
            
            for field in mapped_field_ids:
                nodes = doc.xpath("//field[@name='%s']" % field.name)
                for node in nodes:
                    node.set('class', 'magento-mapped-field-view')
                    help = node.get('help', '')
                    node.set('help', '** Magento ** \n %s' % help)
                    setup_modifiers(
                        node, res['fields'][field.name])                    
            res['arch'] = etree.tostring(doc)
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

#     def create(self, data):
#         """ Create a record on the external system """
#         if self.work.magento_api._location.version == '2.0':
#             new_product = super(ProductTemplateAdapter, self)._call(
#                 'products', {
#                     'product': data
#                 },
#                 http_method='post')
#             return new_product['id']

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
        # XXX actually only ol_catalog_product.update works
        # the PHP connector maybe breaks the catalog_product.update
        if self.work.magento_api._location.version == '2.0':
            _logger.info("Prepare to call api with %s " % data)
            # Replace by the
            id = data['sku']
            storeview_id = self.work.storeview_id or False
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
