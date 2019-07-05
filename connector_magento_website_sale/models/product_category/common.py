# -*- coding: utf-8 -*-
# © 2019 Callino
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class MagentoProductCategory(models.Model):
    _inherit = 'magento.product.category'

    # Use product.public.category if website_sale is installed
    public_categ_id = fields.Many2one(comodel_name='product.public.category',
                                      string='Public Product Category',
                                      required=False,
                                      ondelete='cascade')

    @api.multi
    def update_products(self):
        '''
        We do need to overwrite this here complete
        :return:
        '''
        for mcategory in self:
            # Get tmpl_ids from magento.product.template
            mtemplates = self.env['magento.product.template'].search([
                ('public_categ_ids', 'in', mcategory.public_categ_id.id),
                ('backend_id', '=', mcategory.backend_id.id),
            ])
            mbundles = self.env['magento.product.bundle'].search([
                ('public_categ_ids', 'in', mcategory.public_categ_id.id),
                ('backend_id', '=', mcategory.backend_id.id),
            ])
            mproducts = self.env['magento.product.product'].search([
                ('public_categ_ids', 'in', mcategory.public_categ_id.id),
                ('magento_configurable_id', '=', False),
                ('backend_id', '=', mcategory.backend_id.id),
            ])
            tmpl_ids = [mtemplate.odoo_id.id for mtemplate in mtemplates]
            tmpl_ids.extend(mbundle.odoo_id.id for mbundle in mbundles if mbundle.odoo_id.id not in tmpl_ids)
            tmpl_ids.extend(mproduct.odoo_id.product_tmpl_id.id for mproduct in mproducts if mproduct.odoo_id.product_tmpl_id.id not in tmpl_ids)
            _logger.info("This product template ids are in this category: %s", tmpl_ids)
            # Get list of ids already with position entry
            pt_ids = {}
            for pp in mcategory.product_position_ids:
                pt_ids[pp.product_template_id] = pp.id
            p_tmpl_ids = pt_ids.keys()
            ppids = []
            missing = list(set(tmpl_ids) - set(p_tmpl_ids))
            # Create missing entries
            for tmpl_id in missing:
                ppids.append((0, 0, {
                    'product_template_id': tmpl_id,
                    'magento_product_category_id': mcategory.id,
                    'position': 9999,
                }))
            # Remove entries lost
            delete = list(set(p_tmpl_ids) - set(tmpl_ids))
            for tmpl_id in delete:
                ppids.append((3, pt_ids[tmpl_id]))
            if ppids:
                mcategory.with_context(connector_no_export=True).product_position_ids = ppids
                mcategory.with_delay(identity_key=('magento_product_category_position_%s'%mcategory.id)).update_positions()


class ProductCategory(models.Model):
    _inherit = 'product.public.category'

    magento_bind_ids = fields.One2many(
        comodel_name='magento.product.category',
        inverse_name='public_categ_id',
        string="Magento Bindings",
    )
