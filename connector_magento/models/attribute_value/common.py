import logging
from odoo import models, fields, api
from odoo.addons.component.core import Component
import urllib
_logger = logging.getLogger(__name__)



class MagentoProductAttributevalue(models.Model):
    _name = 'magento.product.attribute.value'
    _inherit = 'magento.binding'
    _inherits = {'product.attribute.value': 'odoo_id'}
    _description = 'Magento attribute value'
    
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
    main_text_code = fields.Char('Main text code eg. swatch or default value')
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
        if 'attribute_id' not in vals:
            # On first create we do need this because attribute_id is missing
            vals['attribute_id'] = self.env['magento.product.attribute'].browse(vals['magento_attribute_id']).odoo_id.id
        return super(MagentoProductAttributevalue, self).create(vals)


class ProductAttributevalue(models.Model):
    _inherit = 'product.attribute.value'

    magento_bind_ids = fields.One2many(
        comodel_name='magento.product.attribute.value',
        inverse_name='odoo_id',
        string='Magento Bindings',
    )
    
    

# class ProductAttributeValueBinder(Component):
#     """ Bind records and give odoo/magento ids correspondence
# 
#     Binding models are models called ``magento.{normal_model}``,
#     like ``magento.res.partner`` or ``magento.product.product``.
#     They are ``_inherits`` of the normal models and contains
#     the Magento ID, the ID of the Magento Backend and the additional
#     fields belonging to the Magento instance.
#     """
#     _name = 'magento.product.attribute.value.binder'
#     _inherit = 'magento.binder'
#     _apply_on = ['magento.product.attribute.value']
#     
# #     _usage = 'binder'
    

class ProductAttributeValueAdapter(Component):
    _name = 'magento.product.attribute.value.adapter'
    _inherit = 'magento.adapter'
    _apply_on = 'magento.product.attribute.value'

    _magento2_model = 'products/attributes/%(attributeCode)s/options'
    _magento2_search = 'options'
    _magento2_key = 'id'
    _magento2_name = 'option'

    def read(self, id, storeview_code=None, attributes=None, binding=None):
        """ Returns the information of a record

        :rtype: dict
        """
        if self.work.magento_api._location.version == '2.0':
            # TODO: storeview_code context in Magento 2.0
            res_admin = super(ProductAttributeValueAdapter, self).read(
                id, attributes=attributes, storeview_code='all')
            if res:
                for attr in res.get('custom_attributes', []):
                    res[attr['attribute_code']] = attr['value']
            return res
        return super(ProductAttributeAdapter, self).read(id, storeview_code=None, attributes=None)

    def _create_url(self, binding=None):
        return '%s' % (self._magento2_model % {'attributeCode': binding.magento_attribute_id.attribute_code})

    def delete(self, magento_value_id, magento_attribute_id):
        def escape(term):
            if isinstance(term, basestring):
                return urllib.quote(term.encode('utf-8'), safe='')
            return term
        """ Delete a record on the external system """
        if self.work.magento_api._location.version == '2.0':
            res = self._call('%s/%s' % (self._magento2_model % {'attributeCode': magento_attribute_id}, escape(magento_value_id)), http_method="delete")
            return res
        return self._call('%s.delete' % self._magento_model, [int(id)])

    def _get_id_from_create(self, result, data=None):
        return data['value']
