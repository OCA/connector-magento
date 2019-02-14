# -*- coding: utf-8 -*-
# Copyright <YEAR(S)> <AUTHOR(S)>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import xmlrpclib
import ast
from odoo import api, models, fields
from odoo.addons.component.core import Component
from odoo.addons.queue_job.job import job, related_action
from odoo.addons.connector.exception import IDMissingInBackend

_logger = logging.getLogger(__name__)



class MagentoProductTemplate(models.Model):
    _name = 'magento.product.template'
    _inherit = 'magento.binding'
    _inherits = {'product.template': 'odoo_id'}
    _description = 'Magento Product Template'
    
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

    @api.depends('odoo_id',)
    @api.multi
    def _is_configurable(self):
        self.ensure_one()
        self.product_type = 'simple'
        if self.odoo_id.product_variant_count > 1:
            self.product_type = 'configurable'
        
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
    
    created_at = fields.Date('Created At (on Magento)')
    updated_at = fields.Date('Updated At (on Magento)')
    product_type = fields.Selection(selection='product_type_get',
                                    string='Magento Product Type',
                                    compute=_is_configurable,
                                    required=True)
    
    magento_template_attribute_line_ids = fields.One2many(
                    comodel_name='magento.custom.template.attribute.values', 
                    inverse_name='magento_product_template_id', 
                    string='Magento Simple Custom Attributes Values for templates',
                                        )
    
    
    @api.multi
    def export_product_template_button(self, fields=None):
        self.ensure_one()
        self.with_delay(priority=20).export_product_template()

        
    @job(default_channel='root.magento')
    @related_action(action='related_action_unwrap_binding')
    @api.multi
    def export_product_template(self, fields=None):
        """ Export the attributes configuration of a product. """
        self.ensure_one()
        with self.backend_id.work_on(self._name) as work:
            #TODO make different usage
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
    
class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    
    magento_template_bind_ids = fields.One2many(
        comodel_name='magento.product.template',
        inverse_name='odoo_id',
        string='Magento Template Bindings',
    )     
   
    @api.model
    def fields_view_get(self, *args, **kwargs):
        res = super(ProductTemplate, self).fields_view_get(*args, **kwargs)
        #TODO : Implement method to identify if the field is mapped with Magento
        # If yes, push a class to highlight the principle.
        
#         timebox_model = self.env['project.gtd.timebox']
#         if (res['type'] == 'fo') and self.env.context.get('gtd', False):
#             timeboxes = timebox_model.search([])
#             search_extended = ''
#             for timebox in timeboxes:
#                 filter_ = u"""
#                     <filter domain="[('timebox_id', '=', {timebox_id})]"
#                             string="{string}"/>\n
#                     """.format(timebox_id=timebox.id, string=timebox.name)
#                 search_extended += filter_
#             search_extended += '<separator orientation="vertical"/>'
#             res['arch'] = tools.ustr(res['arch']).replace(
#                 '<separator name="gtdsep"/>', search_extended)

        return res
   

    @api.multi
    def write(self, vals):
        org_vals = vals.copy()
        res = super(ProductTemplate, self).write(vals)
        variant_ids = self.product_variant_ids
        prod_ids = variant_ids.filtered(lambda p: len(p.magento_bind_ids) > 0)
        for var  in prod_ids:
            for prod in var.magento_bind_ids:
                for key in org_vals:
                    prod.check_field_mapping(key, vals)
        return res              




class ProductTemplateAdapter(Component):
    _name = 'magento.product.template.adapter'
    _inherit = 'magento.adapter'
    _apply_on = 'magento.product.template'
    
    _magento_model = 'catalog_product'
    _magento2_model = 'products'
    _magento2_search = 'products'
    _magento2_key = 'sku'
    _admin_path = '/{model}/edit/id/{id}'
    
    
    def create(self, data):
        """ Create a record on the external system """
        if self.work.magento_api._location.version == '2.0': 
            datas = self.get_product_datas(data)
            datas['product'].update(data)
            new_product = super(ProductTemplateAdapter, self)._call(
                'products', datas , 
                http_method='post')            
            return new_product['id']
             
             
        return self._call('%s.create' % self._magento_model,
                          [customer_id, data])
    
    
    
    def get_product_datas(self, data, id=None, saveOptions=True):
        """ Hook to implement in other modules"""
        visibility = 4 
        
        product_datas = {
            'product': {
                "sku": data['sku'] or data['default_code'],
                "name": data['name'],
                "attributeSetId": data['attributeSetId'],
                "price": 0,
                "status": 1,
                "visibility": visibility,
                "typeId": data['typeId'],
                "weight": data['weight'] or 0.0,
#                           
            }
            ,"saveOptions": saveOptions
            }
        if id is None:
            product_datas['product'].update({'id': 0})
        return product_datas


    def write(self, id, data, storeview_id=None):
        """ Update records on the external system """
        # XXX actually only ol_catalog_product.update works
        # the PHP connector maybe breaks the catalog_product.update
        if self.work.magento_api._location.version == '2.0':
            datas = self.get_product_datas(data, id)
            datas['product'].update(data)
            _logger.info("Prepare to call api with %s " % datas)
            #Replace by the 
            id  = data['sku']
            super(ProductTemplateAdapter, self)._call(
                'products/%s' % id, datas, 
                http_method='put')
            
            stock_datas = {"stockItem":{
                'is_in_stock': True}}
            return super(ProductTemplateAdapter, self)._call(
                    'products/%s/stockItems/1' % id, 
                    stock_datas, 
                    http_method='put')
#             raise NotImplementedError  # TODO
        return self._call('ol_catalog_product.update',
                          [int(id), data, storeview_id, 'id'])
