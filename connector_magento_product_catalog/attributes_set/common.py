import logging
from odoo import models, fields, api
from odoo.addons.connector.exception import IDMissingInBackend
from odoo.addons.component.core import Component
from odoo.addons.component_event import skip_if
from odoo.addons.queue_job.job import job, related_action

_logger = logging.getLogger(__name__)

class MagentoProductAttributesSet(models.Model):
    _name = 'magento.product.attributes.set'
    _inherit = 'magento.binding'
    _description = 'Magento attribute set'
    
    name = fields.Char(string = 'Set Name')
    attribute_ids = fields.Many2many('product.attribute', string='Attribute(s)')
    website_ids = fields.Many2many(comodel_name='magento.website',
                                   string='Websites')
    created_at = fields.Date('Created At (on Magento)')
    updated_at = fields.Date('Updated At (on Magento)')
    
