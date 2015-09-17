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

    def testExportProductApi(self):
        """
        
        """
        job_path = ('openerp.addons.magentoerpconnect_catalog_simple.'
                    'models.magento_product.exporter.export_product')
        response = {
            'ol_catalog_product.create': 177,
        }
        with mock_job_delay_to_direct(job_path), \
                mock_api(response, key_func=lambda m, a: m) as calls_done:
            product = self.env['product.product'].create(
                {'name': 'TEST export',
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
                )
            self.assertEqual(len(calls_done), 1)
            method, args_tuple = calls_done[0]
            self.assertEqual(method, 'ol_catalog_product.create')
            
#     def test_export_invoice_api(self):
#         """ Exporting an invoice: call towards the Magento API """
#         job_path = ('openerp.addons.magentoerpconnect.'
#                     'invoice.export_invoice')
#         response = {
#             'sales_order_invoice.create': 987654321,
#         }
#         # we setup the payment method so it exports the invoices as soon
#         # as they are validated (open)
#         self.payment_method.write({'create_invoice_on': 'open'})
#         self.stores.write({'send_invoice_paid_mail': True})
#  
#         with mock_job_delay_to_direct(job_path), \
#                 mock_api(response, key_func=lambda m, a: m) as calls_done:
#             self._invoice_open()
#  
#             # Here we check what call with which args has been done by the
#             # BackendAdapter towards Magento to create the invoice
#             self.assertEqual(len(calls_done), 1)
#             method, (mag_order_id, items,
#                      comment, email, include_comment) = calls_done[0]
#             self.assertEqual(method, 'sales_order_invoice.create')
#             self.assertEqual(mag_order_id, '900000691')
#             self.assertEqual(items, {'1713': 1.0, '1714': 1.0})
#             self.assertEqual(comment, _("Invoice Created"))
#             self.assertEqual(email, True)
#             self.assertFalse(include_comment)
#  
#         self.assertEquals(len(self.invoice.magento_bind_ids), 1)
#         binding = self.invoice.magento_bind_ids
#         self.assertEquals(binding.magento_id, '987654321')
