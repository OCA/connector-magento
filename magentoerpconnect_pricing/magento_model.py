# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2013-2015 Camptocamp SA
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
##############################################################################

from openerp import models, fields, api, _
from openerp.addons.connector.session import ConnectorSession
from .product import export_product_price


class MagentoBackend(models.Model):
    _inherit = 'magento.backend'

    @api.model
    def _get_pricelist_id(self):
        return self.env.ref('product.list0')

    pricelist_id = fields.Many2one(comodel_name='product.pricelist',
                                   string='Pricelist',
                                   required=True,
                                   default=_get_pricelist_id,
                                   domain="[('type', '=', 'sale')]",
                                   help='The price list used to define '
                                        'the prices of the products in '
                                        'Magento.')
    update_prices = fields.Boolean(default=True,
                                   help='Whether prices according to the '
                                        'selected pricelist are pushed '
                                        'to Magento')

    @api.onchange('pricelist_id')
    def onchange_pricelist_id(self):
        if not self.id:
            # no warning for new records
            return
        warning = {
            'title': _('Warning'),
            'message': _('If you change the pricelist of the backend, '
                         'the price of all the products will be updated '
                         'in Magento.')
        }
        return {'warning': warning}

    @api.multi
    def _update_default_prices(self):
        """ Update the default prices of the products linked with
        this backend.

        The default prices are linked with the 'Admin' website (id: 0).
        """
        backend_ids = self.filtered('update_prices').ids
        website_model = self.env['magento.website']
        websites = website_model.search([('backend_id', 'in', backend_ids),
                                         ('magento_id', '=', '0')])
        websites.update_all_prices()

    @api.multi
    def write(self, vals):
        if 'pricelist_id' in vals:
            self._update_default_prices()
        return super(MagentoBackend, self).write(vals)


class MagentoWebsite(models.Model):
    _inherit = 'magento.website'

    pricelist_id = fields.Many2one(comodel_name='product.pricelist',
                                   string='Pricelist',
                                   domain="[('type', '=', 'sale')]",
                                   help='The pricelist used to define the '
                                        'currency of the orders of this '
                                        'website and, if price update is '
                                        'activated on the backend, '
                                        'the prices of the products in '
                                        'Magento for this website.\n'
                                        'Choose a pricelist only if the '
                                        'prices are different for this '
                                        'website.\n'
                                        'When empty, the default price '
                                        'will be used.')

    @api.multi
    def update_all_prices(self):
        """ Update the prices of all the products linked to the website. """
        session = ConnectorSession(self.env.cr, self.env.uid,
                                   context=self.env.context)
        for website in self.filtered('backend_id.update_prices'):
            if website.magento_id == '0':
                # 'Admin' website -> default values
                # Update the default prices on all the products.
                binding_ids = website.backend_id.product_binding_ids
            else:
                binding_ids = website.product_binding_ids
            for binding in binding_ids:
                export_product_price.delay(session,
                                           'magento.product.product',
                                           binding.id,
                                           website_id=website.id)
        return True

    @api.onchange('pricelist_id')
    def onchange_pricelist_id(self):
        warning = {
            'title': _('Warning'),
            'message': _('If you change the pricelist of the website, '
                         'the price of all the products linked with this '
                         'website will be updated in Magento if the price '
                         'update is active on the backend.')
        }
        return {'warning': warning}

    @api.multi
    def write(self, vals):
        if 'pricelist_id' in vals:
            self.update_all_prices()
        return super(MagentoWebsite, self).write(vals)
