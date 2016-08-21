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
from openerp.addons.connector.session import ConnectorSession
from .event import on_product_create, on_product_write
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
        bkend_obj = self.env['magento.backend']
        bkend_brw = bkend_obj.browse(backend_id)
        return {
            'backend_id': backend_id,
            'openerp_id': self.id,
            'visibility': '4',
            'status': '1',
            'created_at': fields.Date.today(),
            'updated_at': fields.Date.today(),
            'tax_class_id': bkend_brw.default_mag_tax_id.id
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
        self_context = self.with_context(from_product_ids=self.ids)
        result = super(ProductProduct, self_context).write(vals)
        session = ConnectorSession.from_env(self.env)
        for product_id in self.ids:
            on_product_write.fire(session, self._name, product_id, vals)

        if vals.get('active', True) is False:
            for product in self:
                for bind in product.magento_bind_ids:
                    bind.write({'active': False})

        if 'sale_ok' in vals:
            for product in self:
                product.automatic_binding(vals['sale_ok'])

        return result

    @api.model
    def create(self, vals):
        self_context = self.with_context(from_product_ids=self.ids)
        product = super(ProductProduct, self_context).create(vals)
        session = ConnectorSession.from_env(self.env)
        on_product_create.fire(session, self._name, product.id, vals)
        if product.sale_ok:
            if not product._context.get('connector_no_export', False):
                product.automatic_binding(True)

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


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.multi
    def write(self, vals):
        result = super(ProductTemplate, self).write(vals)
        # If a field of the template has been modified, we want to
        # export this field on all the variants on this product.
        # If only fields of variants have been modified, they have
        # already be exported by the event on 'product.product'
        if any(field for field in vals if field in self._columns):
            session = ConnectorSession.from_env(self.env)
            variants = self.mapped('product_variant_ids')
            # When the 'write()' is done on 'product.product', avoid
            # to fire the event 2 times. Event has been fired on the
            # variant, do not fire it on the template.
            # We'll export the *other* variants of the template though
            # as soon as template fields have been modified.
            if self.env.context.get('from_product_ids'):
                from_product_ids = self.env.context['from_product_ids']
                product_model = self.env['product.product']
                triggered_products = product_model.browse(from_product_ids)
                variants -= triggered_products
            for variant_id in variants.ids:
                on_product_write.fire(session, variants._model._name,
                                      variant_id, vals)
        return result
