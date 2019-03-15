import logging
from odoo import models, fields, api
from odoo.addons.connector.exception import IDMissingInBackend
from odoo.addons.component.core import Component
from odoo.addons.component_event import skip_if
from odoo.addons.queue_job.job import job, related_action, identity_exact

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
    created_at = fields.Date('Created At (on Magento)')
    updated_at = fields.Date('Updated At (on Magento)')
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
    
    attribute_set_ids = fields.Many2many('magento.product.attributes.set', 
                                         string='Attribute_set(s)')
    is_pivot_attribute = fields.Boolean(string="Magento Pivot Attribute", default=False)

    _sql_constraints = [
        ('product_attribute_backend_uniq', 'unique(odoo_id, external_id)', 'This attribute is already mapped to a magento backend!')
    ]
    
    @api.model
    def _is_generate_variant(self, frontend_input):
        if frontend_input in ['select', 'multiselect']:
            return True
        return False

    @api.multi
    def export_product_attribute_button(self, fields=None):
        self.ensure_one()
        lang = self.env['res.lang'].browse(self.backend_id.default_lang_id.id).code
        self.with_delay(priority=20,
                        identity_key=identity_exact).export_product_attribute(fields)

    @job(default_channel='root.magento')
    @related_action(action='related_action_unwrap_binding')
    @api.multi
    def export_product_attribute(self, fields=None):
        """ Export a simple attribute. """
        self.ensure_one()
        with self.backend_id.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            self = self.with_context(fields)
            return exporter.run(self)
    

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
    _magento2_name = 'attribute'
