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
from openerp import models, fields
from openerp.addons.connector.unit.mapper import mapping
from openerp.addons.magentoerpconnect.backend import magento
from openerp.addons.magentoerpconnect.sale import \
    SaleOrderCurrencyImportMapper, SaleOrderPricelistCurrencyAssign


class MagentoSaleOrder(models.Model):
    _inherit = 'magento.sale.order'

    magento_currency_id = fields.Many2one('res.currency', 'Magento Currency')


@magento(replacing=SaleOrderCurrencyImportMapper)
class SaleOrderCurrencyImportMapper(SaleOrderCurrencyImportMapper):
    _model_name = 'magento.sale.order'

    @mapping
    def currency_id(self, record):
        """ Maps magento sale currency """
        currency_model = self.env['res.currency']
        currency = currency_model.search([
            ('name', '=', record['order_currency_code'])
        ])
        return {'magento_currency_id': currency.id}


@magento(replacing=SaleOrderPricelistCurrencyAssign)
class SaleOrderPricelistCurrencyAssign(SaleOrderPricelistCurrencyAssign):
    _model_name = ['magento.sale.order']

    def change_pricelist_currency(self, binding):
        super(SaleOrderPricelistCurrencyAssign, self).\
            change_pricelist_currency(binding)
        if binding.pricelist_id.currency_id != binding.magento_currency_id:
            pricelist = binding.pricelist_id.get_pricelist_for_currency(
                binding.magento_currency_id.id)
            binding.write({'pricelist_id': pricelist.id})
