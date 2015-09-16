# -*- coding: utf-8 -*-
#
#    Author: Damien Crier
#    Copyright 2015 Camptocamp SA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from openerp import api, models, fields
from openerp import exceptions
from openerp.tools.translate import _
import logging
_logger = logging.getLogger(__name__)


class MagentoProductProduct(models.Model):
    _inherit = 'magento.product.product'

    website_ids = fields.Many2many(readonly=False)
    active = fields.Boolean(default=True,
                            help="When a binding is unactivated, the product "
                                 "is delete from Magento. This allow to remove"
                                 " product from Magento and so to increase the"
                                 " perf on Magento side")

    @api.multi
    def write(self, vals):
        if vals.get('active') is True:
            binding_ids = self.search([('active', '=', False)])
            if len(binding_ids) > 0:
                raise exceptions.Warning(
                    _('You can not reactivate the following binding ids: %s '
                      'please add a new one instead') % binding_ids)
        return super(MagentoProductProduct, self).write(vals)

    @api.multi
    def unlink(self):
        synchronized_binding_ids = self.search([
            ('id', 'in', self.ids),
            ('magento_id', '!=', False),
        ])
        if synchronized_binding_ids:
            raise exceptions.Warning(
                _('This binding ids %s can not be remove as '
                  'the field magento_id is not empty.\n'
                  'Please unactivate it instead') % synchronized_binding_ids)
        return super(MagentoProductProduct, self).unlink()


class ProductProduct(models.Model):
    _inherit = 'product.product'

    magento_inactive_bind_ids = fields.One2many(
        'magento.product.product',
        'openerp_id',
        string='Magento Inactive Bindings',
        domain=[('active', '=', False)],
        readonly=True,
        )

    @api.multi
    def _prepare_create_magento_auto_binding(self, backend_id):
        self.ensure_one()
        return {
            'backend_id': backend_id,
            'openerp_id': self.id,
            'visibility': '4',
            'status': '1',
        }

    @api.multi
    def _get_magento_binding(self, backend_id):
        self.ensure_one()
        binding_ids = self.env['magento.product.product'].search([
            ('openerp_id', '=', self.id),
            ('backend_id', '=', backend_id),
        ])
        if binding_ids:
            return binding_ids[0]
        else:
            return None

    @api.multi
    def automatic_binding(self, sale_ok):
        backend_obj = self.env['magento.backend']
        mag_product_obj = self.env['magento.product.product']
        back_rs = backend_obj.search([])
        for backend in back_rs:
            if backend.auto_bind_product:
                for product in self:
                    binding_rs = product._get_magento_binding(backend.id)
                    if not binding_rs and sale_ok:
                        vals = product._prepare_create_magento_auto_binding(
                            backend.id)
                        mag_product_obj.create(vals)
                    else:
                        binding_rs.write({
                            'status': '1' if sale_ok else '2',
                        })

    @api.multi
    def write(self, vals):
        super(ProductProduct, self).write(vals)
        if vals.get('active', True) is False:
            for product in self:
                for bind in product.magento_bind_ids:
                    bind.write({'active': False})
#         if 'sale_ok' in vals:
#             self.automatic_binding(vals['sale_ok'])
        return True

    @api.model
    def create(self, vals):
        product = super(ProductProduct, self).create(vals)
#         if product.sale_ok:
#             product.automatic_binding(True)
        return product

    @api.constrains('name', 'description')
    def _check_description(self):
        if self.name == self.description:
            raise exceptions.ValidationError(
                "Fields name and description must be different")

    @api.one
    @api.constrains('backend_id', 'openerp_id', 'active')
    def _check_uniq_magento_product(self):
        self.env.cr.execute("""SELECT openerp_id
        FROM magento_product_product
        WHERE active=True
        GROUP BY backend_id, openerp_id
        HAVING count(id) > 1""")
        result = self.env.cr.fetchall()
        if result:
            raise exceptions.Warning(
                _('You can not have more than one active binding for '
                  'a product. Here is the list of product ids with a '
                  'duplicated binding : %s')
                % ", ".join([str(x[0]) for x in result]))
        return True
