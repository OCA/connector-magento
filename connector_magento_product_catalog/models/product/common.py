# -*- coding: utf-8 -*-
# Copyright <YEAR(S)> <AUTHOR(S)>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import xmlrpclib
from odoo import api, models, fields
from odoo.addons.component.core import Component
from odoo.addons.queue_job.job import job, related_action
from odoo.addons.queue_job.job import identity_exact
from odoo.addons.connector.exception import IDMissingInBackend

_logger = logging.getLogger(__name__)



class MagentoProductProduct(models.Model):
    _inherit = 'magento.product.product'
    
    attribute_set_id = fields.Many2one('magento.product.attributes.set',                           
                                       string='Attribute set')
    
    magento_attribute_line_ids = fields.One2many(comodel_name='magento.custom.attribute.values', 
                                                 inverse_name='magento_product_id', 
                                                 string='Magento Simple Custom Attributes Values',
                                        )

    @api.multi
    def sync_to_magento(self):
        self.ensure_one()
        with self.backend_id.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            return exporter.run(self)

    @api.multi
    def resync(self):
        self.ensure_one()
        self.with_delay(priority=20,
                        identity_key=identity_exact
                        ).export_product()

    @job(default_channel='root.magento')
    @related_action(action='related_action_unwrap_binding')
    @api.multi
    def export_product(self, fields=None):
        """ Export the attributes configuration of a product. """
        self.ensure_one()
        with self.backend_id.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            return exporter.run(self)

    
    def action_magento_custom_attributes(self):
        action = self.env['ir.actions.act_window'].for_xml_id(
            'connector_magento_product_catalog', 
            'action_magento_custom_attributes')
        
        action['domain'] = unicode([('magento_product_id', '=', self.id)])
        ctx = action.get('context', '{}') or '{}'
        
        action_context = ast.literal_eval(ctx)
        action_context.update({
            'default_attribute_set_id': self.attribute_set_id.id,
            'default_magento_product_id': self.id,
            'search_default_wt_odoo_mapping': True})
#         
# #         action_context = ctx
#         action_context.update({
#             'default_project_id': self.project_id.id})
        action['context'] = action_context
        return action
    
    
    @api.multi
    def check_field_mapping(self, field, vals):
        # Check if the Odoo Field has a matching attribute in Magento
        # Update the value
        # Return an appropriate dictionnary
        self.ensure_one()
#         att_id = 0
        custom_model = self.env['magento.custom.attribute.values']
        odoo_fields = self.env['ir.model.fields'].search([
                    ('name', '=', field),
                    ('model', 'in', ['product.product', 'product.template'])])
        
        att_ids = self.env['magento.product.attribute'].search(
            [('odoo_field_name', 'in', [o.id for o in odoo_fields]),
             ('backend_id', '=', self.backend_id.id)
             ])
        
        if len(att_ids) > 0:
            att_id = att_ids[0]
            values = custom_model.search(
                [('magento_product_id', '=', self.id),
                 ('attribute_id', '=', att_id.id)
                 ])
            custom_vals = {
                    'magento_product_id': self.id,
                    'attribute_id': att_id.id,
                    'attribute_text': self[field],
                    'attribute_select': False,
                    'attribute_multiselect': False,
            }
            odoo_field_type = odoo_fields[0].ttype
            if odoo_field_type in ['many2one', 'many2many'] \
                    and 'text' in att_id.frontend_input:
                custom_vals.update({
                    'attribute_text': str(
                        [v.magento_bind_ids.external_id for v in self[field]
                         ])})
            
            if att_id.frontend_input == 'boolean':
                custom_vals.update({
                    'attribute_text': str(int(self[field]))})
            if att_id.frontend_input == 'select':
                custom_vals.update({
                    'attribute_text': False,
                    'attribute_multiselect': False,
                    'attribute_select': self[field].magento_bind_ids[0].id})
            if att_id.frontend_input == 'multiselect':
                custom_vals.update({
                    'attribute_text': False,
                    'attribute_multiselect': False,
                    'attribute_multiselect': 
                    [(6, False, [
                        v.id for v in self[field].magento_bind_ids] )]})
            if len(values) == 0:    
                custom_model.with_context(no_update=True).create(custom_vals)
            else:
                values.with_context(no_update=True).write(custom_vals)
    

class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    @api.multi
    def write(self, vals):
        org_vals = vals.copy()
        res = super(ProductProduct, self).write(vals)
        prod_ids = self.filtered(lambda p: len(p.magento_bind_ids) > 0)
        for prod in prod_ids:
            for binding in prod.magento_bind_ids:
                for key in org_vals:
                    binding.check_field_mapping(key, vals)
        return res


class ProductProductAdapter(Component):
    _inherit = 'magento.product.product.adapter'

#     def write(self, id, data, storeview_id=None):
#         """ Update records on the external system """
#         # XXX actually only ol_catalog_product.update works
#         # the PHP connector maybe breaks the catalog_product.update
#         if self.work.magento_api._location.version == '2.0':
#             _logger.info("Prepare to call api with %s " % data)
#             return super(ProductProductAdapter, self)._call(
#                 'products/%s' % data['sku'], {
#                     'product': data
#                 },
#                 http_method='put')
#         return self._call('ol_catalog_product.update',
#                           [int(id), data, storeview_id, 'id'])

