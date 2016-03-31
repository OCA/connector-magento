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

import mock
from openerp import fields
from openerp.addons.magentoerpconnect.unit.import_synchronizer import (
    import_record)
from openerp.addons.magentoerpconnect.unit.backend_adapter import (
    MAGENTO_DATETIME_FORMAT,
)
from openerp.addons.magentoerpconnect.tests.common import (
    mock_api,
    mock_job_delay_to_direct,
    mock_urlopen_image,
    SetUpMagentoSynchronized,
)
from openerp.addons.magentoerpconnect.tests.data_base import (
    magento_base_responses,
)
from openerp.addons.magentoerpconnect.tests.data_product import (
    simple_product_and_images,
)


class TestExportPrice(SetUpMagentoSynchronized):

    def setUp(self):
        super(TestExportPrice, self).setUp()
        with mock_api([simple_product_and_images,
                       magento_base_responses]), mock_urlopen_image():
            import_record(self.session, 'magento.product.product',
                          self.backend_id, 122)
        self.binding = self.env['magento.product.product'].search(
            [('backend_id', '=', self.backend_id),
             ('magento_id', '=', 122),
             ],
        )

    def test_default_pricelist(self):
        self.assertEqual(self.backend.pricelist_id,
                         self.env.ref('product.list0'))

    def test_product_change_price(self):
        """ Export a modified price """
        job_path = ('openerp.addons.magentoerpconnect_pricing.'
                    'product.export_product_price')
        magento_sync_date = fields.Datetime.from_string(self.binding.sync_date)
        magento_sync_date = magento_sync_date.strftime(MAGENTO_DATETIME_FORMAT)
        response = {
            'ol_catalog_product.update': True,
            'ol_catalog_product.info': {'updated_at': magento_sync_date},
        }
        self.assertEqual(self.binding.list_price, 22)
        with mock_job_delay_to_direct(job_path), \
                mock_api(response, key_func=lambda m, a: m) as calls_done:
            # The write triggers 'on_product_price_changed'
            # which run the job 'export_product_price'.
            # For the test, we force the job to be run directly instead
            # of delayed
            self.binding.list_price = 42
            self.assertEqual(len(calls_done), 3)
            # The first call is 'ol_catalog_product.info', requests
            # the 'updated_at' date to check if the record has changed
            self.assertEqual(calls_done[0][0], 'ol_catalog_product.info')

            # The second call is the update of the 'default' price, on
            # the website with the id '0'
            method, (product_id, values,
                     website_id, id_type) = calls_done[1]
            self.assertEqual(product_id, 122)
            self.assertEqual(values, {'price': 42})
            self.assertEqual(website_id, '0')
            self.assertEqual(id_type, 'id')

            # The third call is the update of the price on the website
            # '1'. Since we have the same pricelist, it should not send
            # a price with this setup
            method, (product_id, values,
                     website_id, id_type) = calls_done[2]
            self.assertEqual(product_id, 122)
            self.assertEqual(values, {'price': False})
            self.assertEqual(website_id, '1')
            self.assertEqual(id_type, 'id')

    def _create_pricelist(self):
        pricelist = self.env['product.pricelist'].create({
            'name': 'Test Pricelist',
            'type': 'sale',
            'currency_id': self.env.ref('base.EUR').id,
        })
        version = self.env['product.pricelist.version'].create({
            'name': 'Test Version',
            'pricelist_id': pricelist.id,
        })
        self.env['product.pricelist.item'].create({
            'name': 'Test Item',
            'price_version_id': version.id,
            'base': 1,
            'price_surcharge': 10,
        })
        return pricelist

    def test_product_change_price_different_pricelist(self):
        """ Export a modified price """
        job_path = ('openerp.addons.magentoerpconnect_pricing.'
                    'product.export_product_price')
        magento_sync_date = fields.Datetime.from_string(self.binding.sync_date)
        magento_sync_date = magento_sync_date.strftime(MAGENTO_DATETIME_FORMAT)
        public_website = self.env['magento.website'].search(
            [('backend_id', '=', self.backend_id),
             ('magento_id', '=', '1')],
            limit=1,
        )
        public_website.pricelist_id = self._create_pricelist()
        response = {
            'ol_catalog_product.update': True,
            'ol_catalog_product.info': {'updated_at': magento_sync_date},
        }
        self.assertEqual(self.binding.list_price, 22)
        with mock_job_delay_to_direct(job_path), \
                mock_api(response, key_func=lambda m, a: m) as calls_done:
            # The write triggers 'on_product_price_changed'
            # which run the job 'export_product_price'.
            # For the test, we force the job to be run directly instead
            # of delayed
            self.binding.list_price = 42
            self.assertEqual(len(calls_done), 3)
            # The first call is 'ol_catalog_product.info', requests
            # the 'updated_at' date to check if the record has changed
            self.assertEqual(calls_done[0][0], 'ol_catalog_product.info')

            # The second call is the update of the 'default' price, on
            # the website with the id '0'
            method, (product_id, values,
                     website_id, id_type) = calls_done[1]
            self.assertEqual(product_id, 122)
            self.assertEqual(values, {'price': 42})
            self.assertEqual(website_id, '0')
            self.assertEqual(id_type, 'id')

            # The third call is the update of the price on the website
            # '1'. Since we have the same pricelist, it should not send
            # a price with this setup
            method, (product_id, values,
                     website_id, id_type) = calls_done[2]
            self.assertEqual(product_id, 122)
            # the pricelist of the website has a surcharge of 10
            self.assertEqual(values, {'price': 52})
            self.assertEqual(website_id, '1')
            self.assertEqual(id_type, 'id')

    def test_change_pricelist_on_backend(self):
        """ Change pricelist on backend exports all product prices """
        job_path = ('openerp.addons.magentoerpconnect_pricing.'
                    'magento_model.export_product_price')

        admin_website = self.env['magento.website'].search(
            [('backend_id', '=', self.backend_id),
             ('magento_id', '=', '0')],
            limit=1,
        )
        with mock.patch(job_path) as export_product_price:
            # it will update the prices on the default website (id '0')
            self.backend.pricelist_id = self._create_pricelist()
            export_product_price.delay.assert_called_with(
                mock.ANY,
                'magento.product.product',
                self.binding.id,
                website_id=admin_website.id)

    def test_change_pricelist_on_website(self):
        """ Change pricelist on backend exports all product prices """
        job_path = ('openerp.addons.magentoerpconnect_pricing.'
                    'magento_model.export_product_price')

        public_website = self.env['magento.website'].search(
            [('backend_id', '=', self.backend_id),
             ('magento_id', '=', '1')],
            limit=1,
        )
        with mock.patch(job_path) as export_product_price:
            # it will update the prices on the default website (id '0')
            public_website.pricelist_id = self._create_pricelist()
            export_product_price.delay.assert_called_with(
                mock.ANY,
                'magento.product.product',
                self.binding.id,
                website_id=public_website.id)
