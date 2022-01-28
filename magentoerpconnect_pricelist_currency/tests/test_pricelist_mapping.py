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
from openerp.addons.magentoerpconnect.unit.import_synchronizer import (
    import_record)
from openerp.addons.magentoerpconnect.tests.common import \
    SetUpMagentoSynchronized, mock_api, mock_urlopen_image
from openerp.addons.magentoerpconnect.tests.data_base import \
    magento_base_responses
from .data_order_responses import order_responses


class TestPricelistMapping(SetUpMagentoSynchronized):

    def _import_sale_order(self, increment_id, responses=None):
        if responses is None:
            responses = order_responses
        backend_id = self.backend_id
        with mock_api(responses):
            with mock_urlopen_image():
                import_record(self.session,
                              'magento.sale.order',
                              backend_id, increment_id)
        MagentoOrder = self.env['magento.sale.order']
        binding = MagentoOrder.search(
            [('backend_id', '=', backend_id),
             ('magento_id', '=', str(increment_id))]
        )
        self.assertEqual(len(binding), 1)
        return binding

    def _create_mapped_pricelist(self):
        self.pricelist_model = self.env['product.pricelist']
        pricelist_mapping_model = self.env['product.pricelist.mapping']
        pricelist_mapping = pricelist_mapping_model.create({
            'name': 'Default Sale Pricelist'
        })
        self.default_sale_pricelist = self.env.ref('product.list0')
        self.default_sale_pricelist.write({
            'mapping_id': pricelist_mapping.id
        })
        self.sale_pricelist_usd = self.default_sale_pricelist.copy()
        self.sale_pricelist_usd.write({
            'currency_id': self.env.ref('base.USD').id,
            'mapping_id': pricelist_mapping.id
        })

    def test_pricelist_change_for_currency(self):
        """ Test if get_pricelist_for_currency method works well """
        self._create_mapped_pricelist()
        pricelist_usd = self.default_sale_pricelist.get_pricelist_for_currency(
            self.env.ref('base.USD').id)
        self.assertEqual(pricelist_usd.id, self.sale_pricelist_usd.id,
                         "Pricelist must be changed to USD pricelist")

    def test_import_USD_order(self):
        """ Import a Magento Sale with USD currency and check if pricelist
        is in USD too """
        self._create_mapped_pricelist()
        binding = self._import_sale_order(200000301, responses=[
            magento_base_responses, order_responses])
        self.assertEqual(binding.magento_currency_id.id,
                         self.env.ref('base.USD').id)
        self.assertEqual(binding.pricelist_id.id, self.sale_pricelist_usd.id,
                         "Pricelist must be in USD as the order in magento")

    def test_import_USD_order_no_mapped_pricelist(self):
        """ Import a Magento Sale with USD Currency when no mapped pricelists
         are configured in Odoo """
        default_sale_pricelist = self.env.ref('product.list0')
        binding = self._import_sale_order(200000301, responses=[
            magento_base_responses, order_responses])
        self.assertEqual(binding.magento_currency_id.id,
                         self.env.ref('base.USD').id)
        self.assertEqual(binding.pricelist_id.id, default_sale_pricelist.id)
