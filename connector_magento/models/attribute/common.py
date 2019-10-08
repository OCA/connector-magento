import logging
from odoo import models, fields, api
from odoo.addons.component.core import Component
from odoo.addons.queue_job.job import job, related_action, identity_exact


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

    attribute_id = fields.Integer(string='Magento Attribute ID')
    attribute_code = fields.Char(string='Magento Attribute Attribute Code')
    nl2br = fields.Boolean('Enable NL2BR', default=False)
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
        ('None', 'None'),
    ], 'Frontend Input', default='select'
    )

    attribute_set_ids = fields.Many2many('magento.product.attributes.set',
                                         string='Attribute_set(s)')
    is_pivot_attribute = fields.Boolean(string="Magento Pivot Attribute", default=False)

    _sql_constraints = [
        ('product_attribute_backend_uniq', 'unique(odoo_id, external_id, backend_id)',
         'This attribute is already mapped to a magento backend!')
    ]

    @api.model
    def create(self, vals):
        '''
        This can not be correct !
        if 'attribute_set_ids' not in vals:
            backend = self.env['magento.backend'].browse(vals['backend_id'])
            vals['attribute_set_ids'] = [(4, backend.id)]
        '''
        return super(MagentoProductAttribute, self).create(vals)

    @api.multi
    def export_product_attribute_button(self):
        self.ensure_one()
        self.with_delay(priority=20,
                        identity_key=identity_exact).export_product_attribute()

    @api.multi
    def import_product_attribute_button(self):
        self.ensure_one()
        self.with_delay(priority=20,
                        identity_key=identity_exact).import_product_attribute()

    @job(default_channel='root.magento')
    @related_action(action='related_action_unwrap_binding')
    @api.multi
    def export_product_attribute(self, fields=None):
        """ Export a simple attribute. """
        self.ensure_one()
        with self.backend_id.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            return exporter.run(self)

    @job(default_channel='root.magento')
    @related_action(action='related_action_unwrap_binding')
    @api.multi
    def import_product_attribute(self):
        """ Import a simple attribute. """
        self.ensure_one()
        with self.backend_id.work_on(self._name) as work:
            importer = work.component(usage='record.importer')
            return importer.run(self.external_id)


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
    
    
    def read(self, id, storeview_code=None, attributes=None, binding=None):
        """ Returns the information of a record
        :rtype: dict
        """
        if self.work.magento_api._location.version == '2.0':
            # Force the read on all storeviews so that the admin value is returned
            # https://github.com/magento/magento2/issues/3430
            res = super(ProductAttributeAdapter, self).read(
                id, attributes=attributes, storeview_code='all')
            return res
        return super(ProductAttributeAdapter, self).read(id, storeview_code=None, attributes=None)

    def _write_url(self, id, binding=None):
        return '%s/%s' % (self._magento2_model, binding.attribute_code)

    def _get_id_from_create(self, result, data=None):
        # We do need the complete result after the create function - to work on the options...
        return result

    def create(self, data, binding=None, storeview_code=None):
        """ Create a record on the external system """
        if self.work.magento_api._location.version == '2.0':
            if self._magento2_name:
                set_id = data['attribute_set_id']
                group_id = data['attribute_group_id']
                del data['attribute_set_id']
                del data['attribute_group_id']
                new_object = self._call(
                    self._create_url(binding),
                    {self._magento2_name: data,
                     'saveOptions': True}, http_method='post')
                # Make a second call to add the new attribute to the correct attribute set
                # TODO: We need to map the attributeGroups !!!
                self._call(
                    'products/attribute-sets/attributes',
                    {
                        "attributeSetId": set_id,
                        "attributeGroupId": group_id,
                        "attributeCode": new_object['attribute_code'],
                        "sortOrder": 0
                    }, http_method='post')
                if isinstance(new_object, dict):
                    data.update(new_object)
            else:
                new_object = self._call(
                    self._create_url(binding),
                    data, http_method='post')
            return self._get_id_from_create(new_object, data)
        return self._call('%s.create' % self._magento_model, [data])
