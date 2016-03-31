# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
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
##############################################################################

from openerp.addons.magentoerpconnect.unit.import_synchronizer import (
    import_record)
from openerp.addons.magentoerpconnect.tests.common import (
    mock_api,
    mock_urlopen_image,
    SetUpMagentoSynchronized,
)
from openerp.addons.magentoerpconnect.tests.data_base import (
    magento_base_responses,
)
from openerp.addons.magentoerpconnect.tests.data_product import (
    simple_product_and_images,
)


class TestImportPrice(SetUpMagentoSynchronized):

    def test_product_price_first_import(self):
        """ Import the price the first import, then never again """
        def import_product(responses):
            with mock_api([responses, magento_base_responses]):
                with mock_urlopen_image():
                    import_record(self.session, 'magento.product.product',
                                  self.backend_id, 122)
            binding = self.env['magento.product.product'].search(
                [('backend_id', '=', self.backend_id),
                 ('magento_id', '=', 122),
                 ],
            )
            return binding

        key = ('ol_catalog_product.info', (122, None, None, 'id'))
        data_with_new_price = simple_product_and_images.copy()
        # set the price on magento
        data_with_new_price[key]['price'] = 55
        # import the product the first time
        binding = import_product(data_with_new_price)
        self.assertEqual(binding.list_price, 55)
        # change the price on magento
        data_with_new_price[key]['price'] = 60
        # import the product a second time; mean an update
        binding = import_product(data_with_new_price)
        # still 55
        self.assertEqual(binding.list_price, 55)

    def _import_order(self):
        with mock_api(magento_base_responses):
            with mock_urlopen_image():
                import_record(self.session,
                              'magento.sale.order',
                              self.backend_id, 900000691)
        binding_model = self.env['magento.sale.order']
        return binding_model.search(
            [('backend_id', '=', self.backend_id),
             ('magento_id', '=', '900000691'),
             ]
        )

    def _create_pricelist(self):
        pricelist = self.env['product.pricelist'].create({
            'name': 'Test Pricelist',
            'type': 'sale',
            'currency_id': self.env.ref('base.CHF').id,
        })
        self.env['product.pricelist.version'].create({
            'name': 'Test Version',
            'pricelist_id': pricelist.id,
        })
        return pricelist

    def test_sale_order_pricelist_on_backend(self):
        """ Use the pricelist set on the backend """
        pricelist = self._create_pricelist()
        self.backend.pricelist_id = pricelist
        order_binding = self._import_order()
        self.assertEqual(order_binding.pricelist_id, pricelist)

    def test_sale_order_pricelist_on_website(self):
        """ The pricelist of the website override the backend one """
        pricelist = self._create_pricelist()
        website_pricelist = self._create_pricelist()
        self.backend.pricelist_id = pricelist
        self.backend.website_ids.write({'pricelist_id': website_pricelist.id})
        order_binding = self._import_order()
        self.assertEqual(order_binding.pricelist_id, website_pricelist)
