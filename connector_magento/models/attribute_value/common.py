import logging
from odoo import models, fields, api
from odoo.addons.component.core import Component
import urllib
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

    magento_attribute_type = fields.Selection(
         related="magento_attribute_id.frontend_input",
         store=True
        )

    # The real magento code - external_id is a combination of attribute_id + _ + code
    code = fields.Char('Magento Code for the value')

    backend_id = fields.Many2one(
        related='magento_attribute_id.backend_id',
        string='Magento Backend',
        readonly=True,
        store=True,
        # override 'magento.binding', can't be INSERTed if True:
        required=False,
    )


class ProductAttributevalue(models.Model):
    _inherit = 'product.attribute.value'

    magento_bind_ids = fields.One2many(
        comodel_name='magento.product.attribute.value',
        inverse_name='odoo_id',
        string='Magento Bindings',
    )
    

class ProductAttributeValueAdapter(Component):
    _name = 'magento.product.attribute.value.adapter'
    _inherit = 'magento.adapter'
    _apply_on = 'magento.product.attribute.value'

    _magento2_model = 'products/attributes/%(attributeCode)s/options'
    _magento2_search = 'options'
    _magento2_key = 'id'
    _magento2_name = 'option'

    def _create_url(self, binding=None):
        return '%s' % (self._magento2_model % {'attributeCode': binding.magento_attribute_id.attribute_code})

    def delete(self, magento_value_id, magento_attribute_id):
        def escape(term):
            if isinstance(term, basestring):
                return urllib.quote(term, safe='')
            return term
        """ Delete a record on the external system """
        if self.work.magento_api._location.version == '2.0':
            res = self._call('%s/%s' % (self._magento2_model % {'attributeCode': magento_attribute_id}, escape(magento_value_id)), http_method="delete")
            return res
        return self._call('%s.delete' % self._magento_model, [int(id)])

    def _get_id_from_create(self, result, data=None):
        return data['value']
