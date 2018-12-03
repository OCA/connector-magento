import logging
from odoo import models, fields, api
from odoo.addons.connector.exception import IDMissingInBackend
from odoo.addons.component.core import Component
from odoo.addons.component_event import skip_if
from odoo.addons.queue_job.job import job, related_action
from __builtin__ import True

_logger = logging.getLogger(__name__)

class MagentoProductAttribute(models.Model):
    _name = 'magento.product.attribute'
    _inherit = 'magento.binding'
    _inherits = {'product.attribute': 'odoo_id'}
    _description = 'Magento attribute'
    
    odoo_id = fields.Many2one(comodel_name='product.attribute',
                              string='Product attribute',
                              required=True,
                              ondelete='restrict')
    
    magento_attribute_value_ids = fields.One2many(
        comodel_name='magento.product.attribute.value',
        inverse_name='magento_attribute_id',
        string='Magento product attribute value'
    )
    
    odoo_field_name = fields.Many2one(comodel_name='ir.model.fields', 
                                 string="Odoo Field Name",
                                 domain=[('model', 'ilike', 'product.')])
    
    attribute_id = fields.Integer(string='Magento Attribute ID' )
    attribute_code = fields.Char(string='Magento Attribute Attribute Code' )
    frontend_input = fields.Selection([
                                           ('text', 'Text'),
                                           ('textarea', 'Text Area'),
                                           ('select', 'Selection'), 
                                           ('multiselect', 'Multi-Selection'),
                                           ('boolean', 'Yes/No'),
                                           ('date', 'Date'),
                                           ('price', 'Price'),
                                           ('weight', 'Weight'),
                                           ('media_image', 'Media Image'),
                                           ('gallery', 'Gallery'),
                                           ('weee', 'Fixed Product Tax'),
                                           ('None', 'None'), #this option is not a magento native field it will be better to found a generic solutionto manage this kind of custom option
                                           ], 'Frontend Input'
                                          )
    
    attribute_set_ids = fields.Many2many('magento.product.attributes.set', string='Attribute_set(s)')

    _sql_constraints = [
        ('product_attribute_backend_uniq', 'unique(odoo_id, external_id)', 'This attribute is already mapped to a magento backend!')
    ]
    
    @api.model
    def _is_generate_variant(self, frontend_input):
        if frontend_input in ['select', 'multiselect']:
            return True
        return False
    
class ProductAttribute(models.Model):
    _inherit = 'product.attribute'

    magento_bind_ids = fields.One2many(
        comodel_name='magento.product.attribute',
        inverse_name='odoo_id',
        string='Magento Bindings',
    )

    
class ProductAttributeAdapter(Component):
    _name = 'magento.product.attribute.adapter'
    _inherit = 'magento.adapter'
    _apply_on = 'magento.product.attribute'

    _magento2_model = 'products/attributes'
    _magento2_search = 'products/attributes'
    _magento2_key = 'attribute_id'


    def _call(self, method, arguments):
        try:
            return super(ProductAttributeAdapter, self)._call(method, arguments)
        except xmlrpclib.Fault as err:
            # this is the error in the Magento API
            # when the product does not exist
            if err.faultCode == 101:
                raise IDMissingInBackend
            else:
                raise
            





