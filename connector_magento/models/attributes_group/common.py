import logging
from odoo import models, fields, api
from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class MagentoProductAttributesGroup(models.Model):
    _name = 'magento.product.attributes.group'
    _inherit = 'magento.binding'
    _description = 'Magento attribute group'

    name = fields.Char(string='Group Name')
    attribute_set_id = fields.Many2one('magento.product.attributes.set', string='Attribute(s)')


class ProductAttributeGroupAdapter(Component):
    _name = 'magento.product.attributes.group.adapter'
    _inherit = 'magento.adapter'
    _apply_on = 'magento.product.attributes.group'

    _magento2_model = 'products/attribute-sets/groups'
    _magento2_search = 'products/attribute-sets/groups/list'
    _magento2_key = 'attribute_group_id'
