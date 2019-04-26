import logging
from odoo import models, fields, api
from odoo.addons.connector.exception import IDMissingInBackend
from odoo.addons.component.core import Component
from odoo.addons.connector.components.binder import Binder
from odoo.addons.component_event import skip_if
from odoo.addons.queue_job.job import job, related_action
from odoo.addons.connector.exception import MappingError, InvalidDataError

_logger = logging.getLogger(__name__)


class MagentoTemplateAttributeline(models.Model):
    _name = 'magento.template.attribute.line'
    _inherit = 'magento.binding'
    _inherits = {'product.attribute.line': 'odoo_id'}
    _description = 'Magento attribute line'

    odoo_id = fields.Many2one(comodel_name='product.attribute.line',
                              string='Product attribute line',
                              required=True,
                              ondelete='restrict')

    magento_attribute_id = fields.Many2one(comodel_name='magento.product.attribute',
                                           string='Magento Product Attribute',
                                           required=True,
                                           ondelete='cascade',
                                           index=True)
    magento_template_id = fields.Many2one(comodel_name='magento.product.template',
                                          string='Magento Product Template',
                                          required=True,
                                          ondelete='cascade',
                                          index=True)
    magento_product_attribute_value_ids = fields.Many2many(comodel_name='magento.product.attribute.value',
                                                           relation='magent_product_att_values_rel',
                                                           string='Magento Product Values',
                                                           required=True,
                                                           ondelete='cascade',
                                                           index=True)
    label = fields.Char('Label')
    position = fields.Integer('Position')

    backend_id = fields.Many2one(
        related='magento_attribute_id.backend_id',
        string='Magento Backend',
        readonly=True,
        store=True,
        required=False,
    )

    @api.model
    def write(self, vals):
        # Do read product_tmpl_id using the magento_tmpl_id
        #tmpl_binding = self.env['magento.product.template'].browse(vals['magento_template_id'])
        #vals['product_tmpl_id'] = tmpl_binding.odoo_id.id
        # Do resolve the attribute id from the magento binding
        binding = self.env['magento.product.attribute'].browse(vals['magento_attribute_id'])
        vals['attribute_id'] = binding.odoo_id.id
        line = super(MagentoTemplateAttributeline, self).write(vals)
        return line

    @api.model
    def create(self, vals):
        # Do read product_tmpl_id using the magento_tmpl_id
        tmpl_binding = self.env['magento.product.template'].browse(vals['magento_template_id'])
        vals['product_tmpl_id'] = tmpl_binding.odoo_id.id
        # Do resolve the attribute id from the magento binding
        binding = self.env['magento.product.attribute'].browse(vals['magento_attribute_id'])
        vals['attribute_id'] = binding.odoo_id.id
        return super(MagentoTemplateAttributeline, self).create(vals)


    def _update_attribute_lines(self, magento_template_id):
        magento_template_id.magento_template_attribute_line_ids.unlink()
        with magento_template_id.backend_id.work_on('magento.product.attribute.value') as work:
            model = work.env['magento.template.attribute.line']
            binder = work.component(usage='binder')
            
            for l in magento_template_id.odoo_id.attribute_line_ids:
                magento_value_ids = []
                for v in l.value_ids:
                    odoo_magento_value = binder.to_external(v, wrap=True)
                    if not odoo_magento_value:
                        raise MappingError("The product attribute value with "
                                           "magento id %s is not imported." %
                                       value['value_index'])
                    magento_value_id = binder.to_internal(odoo_magento_value)
                    magento_value_ids.append(magento_value_id.id)
                    
                res = model.create({
                    'odoo_id': l.id,
                    'magento_template_id': magento_template_id.id,
                    'magento_attribute_id': magento_value_id.magento_attribute_id.id,
                    'magento_product_attribute_value_ids':  [
                        (6, False, magento_value_ids)]
                    })
         
            _logger.debug('found')
        

class ProductAttributeline(models.Model):
    _inherit = 'product.attribute.line'

    magento_bind_ids = fields.One2many(
        comodel_name='magento.template.attribute.line',
        inverse_name='odoo_id',
        string='Magento Bindings',
    )
    
