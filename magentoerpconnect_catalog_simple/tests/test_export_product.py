# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2013 Camptocamp SA
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

import openerp.tests.common as common
from openerp import _
from openerp.addons.connector.session import ConnectorSession
from openerp.addons.magentoerpconnect.unit.import_synchronizer import (
    import_batch,
    import_record)
from openerp.addons.magentoerpconnect.tests.common import (mock_api,
    mock_job_delay_to_direct,
    mock_urlopen_image)
from openerp.addons.magentoerpconnect.tests.data_base import (
    magento_base_responses)


class TestExportProduct(common.TransactionCase):
    """ Test the export of an invoice to Magento """

    def setUp(self):
        super(TestExportProduct, self).setUp()
        backend_model = self.env['magento.backend']
#         self.mag_sale_model = self.env['magento.sale.order']
        self.mag_tax_class_obj = self.env['magento.tax.class']
        self.session = ConnectorSession(self.env.cr, self.env.uid,
                                        context=self.env.context)
        warehouse = self.env.ref('stock.warehouse0')
        self.backend = backend = backend_model.create(
            {'name': 'Test Magento',
             'version': '1.7',
             'location': 'http://anyurl',
             'username': 'guewen',
             'warehouse_id': warehouse.id,
             'password': '42'})
        # create taxes
        default_tax_list = [
            {'name': 'default', 'magento_id': '0'},
            {'name': 'Taxable Goods', 'magento_id': '1'},
            {'name': 'normal', 'magento_id': '2'},
            {'name': 'Shipping', 'magento_id': '3'},
            ]
        if not backend.tax_imported:
            for tax_dict in default_tax_list:
                tax_dict.update(backend_id=backend.id)
                self.mag_tax_class_obj.create(tax_dict)
            backend.tax_imported = True
        # import the base informations
        with mock_api(magento_base_responses):
            import_batch(self.session, 'magento.website', backend.id)
            import_batch(self.session, 'magento.store', backend.id)
            import_batch(self.session, 'magento.storeview', backend.id)
            import_batch(self.session, 'magento.attribute.set', backend.id)
#             with mock_urlopen_image():
#                 import_record(self.session,
#                               'magento.sale.order',
#                               backend.id, 900000691)
        self.stores = self.backend.mapped('website_ids.store_ids')
#         sales = self.mag_sale_model.search(
#             [('backend_id', '=', backend.id),
#              ('magento_id', '=', '900000691')])
#         self.assertEqual(len(sales), 1)
#         self.mag_sale = sales
#         # ignore exceptions on the sale order
#         self.mag_sale.ignore_exceptions = True
#         self.mag_sale.openerp_id.action_button_confirm()
#         sale = self.mag_sale.openerp_id
#         invoice_id = sale.action_invoice_create()
#         assert invoice_id
#         self.invoice_model = self.env['account.invoice']
#         self.invoice = self.invoice_model.browse(invoice_id)

    def testCreateProductApi(self):
        """
        
        """
        job_path = ('openerp.addons.magentoerpconnect.consumer.export_record')
        response = {
            'ol_catalog_product.create': 177,
        }
        with mock_job_delay_to_direct(job_path), \
                mock_api(response, key_func=lambda m, a: m) as calls_done:
            vals = {
                'name': 'TEST export',
                'default_code': 'default_code-export',
                'description': 'description',
                'description_sale': 'description sale',
                'weight': 4.56,
                'active': True,
                'magento_bind_ids': [
                    (0,0,{
                        'backend_id': self.backend.id,
                        'website_ids': [
                            (6, 0, 
                            self.env['magento.website'].search(
                                [('backend_id', '=', self.backend.id)]
                                ).ids
                            )
                        ],
                        'updated_at': '2015-09-17',
                        'created_at': '2015-09-17',
                        'active': True,
                        }
                    )],
                'lst_price': 1.23,
                'attribute_set_id': self.env['magento.attribute.set'].search(
                                        [('magento_id', '=', '9')]).id,
                 }
            product = self.env['product.product'].create(vals)
            self.assertEqual(len(calls_done), 1)
            method, args_tuple = calls_done[0]
            self.assertEqual(method, 'ol_catalog_product.create')

    def testWriteProductApi(self):
        """

        """
        job_path = ('openerp.addons.magentoerpconnect.consumer.export_record')
        response = {
            'ol_catalog_product.create': 177,
        }
        with mock_job_delay_to_direct(job_path), \
                mock_api(response, key_func=lambda m, a: m) as calls_done:
            vals = {
                'name': 'TEST export',
                'default_code': 'default_code-export',
                'description': 'description',
                'description_sale': 'description sale',
                'weight': 4.56,
                'active': True,
                'magento_bind_ids': [
                    (0,0,{
                        'backend_id': self.backend.id,
                        'website_ids': [
                            (6, 0,
                            self.env['magento.website'].search(
                                [('backend_id', '=', self.backend.id)]
                                ).ids
                            )
                        ],
                        'updated_at': '2015-09-17',
                        'created_at': '2015-09-17',
                        'active': True,
                        }
                    )],
                'lst_price': 1.23,
                'attribute_set_id': self.env['magento.attribute.set'].search(
                                        [('magento_id', '=', '9')]).id,
                 }
            product = self.env['product.product'].create(vals)
            self.assertEqual(len(calls_done), 1)
            method, args_tuple = calls_done[0]
            self.assertEqual(method, 'ol_catalog_product.create')
            
        response_write = {'ol_catalog_product.update': True}
        with mock_job_delay_to_direct(job_path), \
            mock_api(response_write, key_func=lambda m, a: m) as calls_done_write:
            product.write({'lst_price': 4.56})
            self.assertEqual(len(calls_done_write), 1)
            # raises because it launches write for product.template
            # AND product.product objects
            wmethod, wargs_tuple = calls_done_write[0]
            self.assertEqual(wmethod, 'ol_catalog_product.update')
