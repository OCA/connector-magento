import logging
from odoo import models, fields, api
from odoo.addons.connector.exception import IDMissingInBackend
from odoo.addons.component.core import Component
from odoo.addons.component_event import skip_if
from odoo.addons.queue_job.job import job, related_action

_logger = logging.getLogger(__name__)



class MagentoProductAttributevalue(models.Model):
    _name = 'magento.product.attribute.value'
    _inherit = 'magento.binding'
    _inherits = {'product.attribute.value': 'odoo_id'}
    _description = 'Magento attribute'
    
    odoo_id = fields.Many2one(comodel_name='product.attribute.value',
                              string='Product attribute value',
                              required=True,
                              ondelete='restrict')
    
    
    magento_attribute_id = fields.Many2one(comodel_name='magento.product.attribute',
                                       string='Magento Product Attribute',
                                       required=True,
                                       ondelete='cascade',
                                       index=True)

    code = fields.Char('Magento Code for the value')
    
    backend_id = fields.Many2one(
        related='magento_attribute_id.backend_id',
        string='Magento Backend',
        readonly=True,
        store=True,
        # override 'magento.binding', can't be INSERTed if True:
        required=False,
    )

    
    @api.model
    def create(self, vals):
        magento_attribute_id = vals['magento_attribute_id']
        binding = self.env['magento.product.attribute'].browse(magento_attribute_id)
        vals['attribute_id'] = binding.odoo_id.id
        exist = self.env['product.attribute.value'].search([('name','=',vals.get('name')),('attribute_id','=',vals['attribute_id'])])
        if exist:
            binging = exist[0]
        else:
            binding = super(MagentoProductAttributevalue, self).create(vals)
        return binding
    
    
class ProductAttributevalue(models.Model):
    _inherit = 'product.attribute.value'

    magento_bind_ids = fields.One2many(
        comodel_name='magento.product.attribute.value',
        inverse_name='odoo_id',
        string='Magento Bindings',
    )
    



