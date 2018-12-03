# -*- coding: utf-8 -*-
# Copyright <YEAR(S)> <AUTHOR(S)>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import xmlrpclib
from odoo import api, models, fields
from odoo.addons.component.core import Component
from odoo.addons.queue_job.job import job, related_action
from odoo.addons.connector.exception import IDMissingInBackend

_logger = logging.getLogger(__name__)



class MagentoProductTemplate(models.Model):
    _name = 'magento.product.template'
    
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
                                    default='simple',
                                    required=True)
    
#     manage_stock = fields.Selection(
#         selection=[('use_default', 'Use Default Config'),
#                    ('no', 'Do Not Manage Stock'),
#                    ('yes', 'Manage Stock')],
#         string='Manage Stock Level',
#         default='use_default',
#         required=True,
#     )
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
    
    magento_bind_ids = fields.One2many(
        comodel_name='magento.product.template',
        inverse_name='odoo_id',
        string='Magento Bindings',
    )

    
    # TODO: report the dependency on the magento.product.product because
    # it's a non sense to force the product to have a single attribute_set and also custom values
#     attribute_set_id = fields.Many2one('magento.product.attributes.set', string='Attribute set')
#     magento_attribute_line_ids = fields.One2many(comodel_name='magento.custom.attribute.values', 
#                                                  inverse_name='product_id', 
#                                                  string='Magento Simple Custom Attributes Values',
#                                         )
#     
#     
#     #TODO: From now, as the mapping is hold by the product, no multi magento instance is supported
#     # Has to be improved
#     def check_field_mapping(self, field, vals):
#         #Check if the Odoo Field has a matching attribute in Magento
#         # Return an appropriate dictionnary
#         
#         att_id = 0
#         odoo_field = self.env['ir.model.fields'].search([
#                     ('name', '=', field),
#                     ('model', '=', self._name)])[0]
#         
#         att_ids = self.env['magento.product.attribute'].search(
#             [('odoo_field_name', '=', odoo_field.id or 0),])
#          
#         if len(att_ids)>0 :
#             att_id = att_ids[0].id
#             if 'magento_attribute_line_ids' in vals and len(vals['magento_attribute_line_ids']) >0:
#                 key_found = False  
#                 for key_dic in vals['magento_attribute_line_ids']:
#                     if key_dic[2]['attribute_color'] == att_id:
#                         key_found = True
#                         key_dic[2]['attribute_text'] = vals[field]
#                 if not key_found:
#                     vals['magento_attribute'].append(
#                     (0, False, {
#                         'attribute_color': att_id,
#                         'attribute_text'  : vals[field]      
#                 }))
#             else:
#                 vals.update({'magento_attribute_line_ids':[]})
#                 att_exists = self.magento_attribute_line_ids.filtered(
#                             lambda a: a.attribute_id.id == att_id)
#                 
#                 if len(att_exists) ==0 :
#                     mode = 0
#                     mode_id = False 
#                 else:
#                     att_exists.unlink()
#                     mode = 0
#                     mode_id = False
#                           
#                 vals['magento_attribute_line_ids'].append(
#                     (mode, mode_id, {
#                         'attribute_id': att_id,
#                         'attribute_text'  : vals[field]
#                 }))
#          
#     
#     def check_attribute_mapping(self, attr):
#         #Check if the attribute modified has a matching field in Odoo
#         # @attr : Tuple coming from a create / write method
#         # Return a dict with field and its value in the proper format
#         # http://www.odoo.com/documentation/10.0/reference/orm.html#model-reference ( CRUD part)
#         
#         odoo_field_name = 0
#         attribute_id = 0
#         
#         if attr[0] == 0 :
#             #Pure Added =>
#             attribute_id = attr[2]['attribute_id']
#             odoo_field_name = attr[2]['odoo_field_name']
#         elif attr[0] == 1 : #Update
#             detail = self.env['magento.custom.attribute.values'].search([('id', '=', attr[1])])
#             odoo_field_name = detail.odoo_field_name.id
#             attribute_id = detail.attribute_id.id
#         
#         odoo_field_ids = self.env['magento.product.attribute'].search([
#             ('odoo_field_name', '=', odoo_field_name),
#             ('odoo_field_name', '!=', False),
#             ('id', '=', attribute_id)
#             ])
#         #TODO: Improve and deal with multiple Magento Instance
#         if len(odoo_field_ids) == 1 :
#             return {odoo_field_ids[0].odoo_field_name.name : attr[2]['attribute_text']}
#         return None
#     
#     
#     @api.multi
#     def write(self, vals):
#         org_vals = vals.copy()
#         for key in org_vals:
#             att_field = None
#             odoo_field = None
#             #Store attributes modes for choosing it 
#             attributes_mode = {}
#              
#             if key == 'magento_attribute_line_ids':
#                 #If magento attribute, find the matching field if exists
#                 for key_att in org_vals['magento_attribute_line_ids']:                     
#                     odoo_field = self.check_attribute_mapping(key_att)
#                     if not odoo_field: continue
#                     vals.update(odoo_field)
#             else:
#                 #if 'magento_attribute' in org_vals :
#                 att_field = self.check_field_mapping(key, vals)
#                 
#  
#         return super(ProductProduct, self).write(vals)                    

     
class ProductTemplateAdapter(Component):
    _name = 'magento.product.template.adapter'
    _inherit = 'magento.adapter'
    _apply_on = 'magento.product.template'
    
    _magento_model = 'catalog_product'
    _magento2_model = 'products'
    _magento2_search = 'products'
    _magento2_key = 'sku'
    _admin_path = '/{model}/edit/id/{id}'
    
    
#     def _create(self, data):
    
#     def create(self, data):
#         """ Create a record on the external system """
#         if self.work.magento_api._location.version == '2.0': 
#             new_product = super(ProductProductAdapter, self)._call(
#                 'products/%s' % id, 
#                 self.get_product_datas(data), 
#                 http_method='put')            
#             return new_product['id']
#             
#             
#         return self._call('%s.create' % self._magento_model,
#                           [customer_id, data])
#     
#     def _get_atts_data(self, binding, fields):
#         """
#         Collect attributes to prensent it regarding to
#         https://devdocs.magento.com/swagger/index_20.html
#         catalogProductRepositoryV1 / POST 
#         """
#         
#         customAttributes = []
#         for values_id in binding.odoo_id.magento_attribute_line_ids:
#             """ Deal with Custom Attributes """            
#             attributeCode = values_id.attribute_id.name
#             value = values_id.attribute_text
#             customAttributes.append({
#                 'attributeCode': attributeCode,
#                 'value': value
#                 })
#             
#         for values_id in binding.odoo_id.attribute_value_ids:
#             """ Deal with Attributes in the 'variant' part of Odoo"""
#             attributeCode = values_id.attribute_id.name
#             value = values_id.name
#             customAttributes.append({
#                 'attributeCode': attributeCode,
#                 'value': value
#                 })
#         result = { 'customAttributes' :  customAttributes }
#         return result
    
    
#     def get_product_datas(self, data, saveOptions=True):
#         main_datas = super(ProductProductAdapter, self).get_product_datas(data, saveOptions)
# #         att = {'customAttributes': data['customAttributes']}
#         
#         main_datas['product'].update(data)
# #         main_datas['product'].update(att)
#         return main_datas
    
