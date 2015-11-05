# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 FactorLibre (http://www.factorlibre.com)
#                  Hugo Santos <hugo.santos@factorlibre.com>
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
from openerp import models, fields, api


class ProductPricelistMapping(models.Model):
    _name = 'product.pricelist.mapping'

    name = fields.Char('Mapping Name', required=True)
    pricelist_ids = fields.One2many('product.pricelist', 'mapping_id',
                                    'Mapped Pricelists')


class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    mapping_id = fields.Many2one('product.pricelist.mapping',
                                 'Pricelist Mapping', index=True)

    @api.multi
    def get_pricelist_for_currency(self, currency_id):
        self.ensure_one()
        if not self.mapping_id:
            return self
        currency_pricelist = self.search([
            ('currency_id', '=', currency_id),
            ('mapping_id', '=', self.mapping_id.id)
        ])
        return currency_pricelist and currency_pricelist[0] or self
