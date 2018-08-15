import logging
from odoo import models, fields, api
from odoo.addons.connector.exception import IDMissingInBackend
from odoo.addons.component.core import Component
from odoo.addons.component_event import skip_if
from odoo.addons.queue_job.job import job, related_action
import xmlrpclib

_logger = logging.getLogger(__name__)

class MagentoProductAttributesSet(models.Model):
    _name = 'magento.product.attributes.set'
    _inherit = 'magento.binding'
    _description = 'Magento attribute set'
    _parent_name = 'backend_id'
    
    name = fields.Char(string = 'Set Name')
    attribute_ids = fields.Many2many('magento.product.attribute', string='Attribute(s)')



class ProductAttributeSetAdapter(Component):
    _name = 'magento.product.attributes.set.adapter'
    _inherit = 'magento.adapter'
    _apply_on = 'magento.product.attributes.set'

    _magento2_model = 'products/attribute-sets'
    _magento2_search = 'products/attribute-sets/sets/list'
    _magento2_key = 'attribute_set_id'
    
    
  
    
    def read_detail(self, id, attributes=None):
        """ Returns the information of a record

        :rtype: dict
        """
        if self.collection.version == '2.0':
            res = self._call('products/attribute-sets/%s/attributes' % id,
                            {'attributes':{}})
            return res

    
