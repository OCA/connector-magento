# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Benoit GUILLOT
#    Copyright 2014 Akretion
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

#import unittest2
#from functools import partial

#from openerp.addons.connector.exception import InvalidDataError
from openerp.addons.magentoerpconnect.tests.test_synchronization import test_base_magento
from openerp.addons.magentoerpconnect.unit.import_synchronizer import (
    import_batch,
    import_record)
from openerp.addons.magentoerpconnect.tests.common import (
    mock_api,
    mock_urlopen_image)
from .test_data_comment import magento_comment_responses
from openerp.addons.magentoerpconnect.unit.export_synchronizer import export_record


class test_import_magento_sale_comment(test_base_magento):
    """ Test the imports from a Magento Mock.

    The data returned by Magento are those created for the
    demo version of Magento on a standard 1.7 version.
    """

    def test_10_import_sale_comment(self):
        """ Test import of sale order comment"""
        backend_id = self.backend_id
        with mock_api(magento_comment_responses):
            with mock_urlopen_image():
                import_record(self.session,
                              'magento.sale.order',
                              backend_id, '100000006')
        order_model = self.registry('magento.sale.order')
        mag_order_ids = order_model.search(
            self.cr, self.uid,
            [('backend_id', '=', backend_id),
             ('magento_id', '=', '100000006')])
        self.assertEqual(len(mag_order_ids), 1)

        order_id = order_model.read(
            self.cr, self.uid, mag_order_ids[0], ['openerp_id'])['openerp_id']
        comment_ids = self.registry('magento.sale.comment').search(
            self.cr, self.uid,
            [('backend_id', '=', backend_id),
             ('res_id', '=', order_id)])
        self.assertEqual(len(comment_ids), 1)
#TODO text import None comment

    def test_20_export_sale_comment(self):
        """ Test export of sale order comment"""
        backend_id = self.backend_id
        response = {
            'sales_order.addComment': True,
        }
        with mock_api(response, method_as_key=True) as calls_done:
            mag_order_model = self.registry('magento.sale.order')
            mag_comment_model = self.registry('magento.sale.comment')
            mail_message_model = self.registry('mail.message')
            #TODO it will be better to avoid to depend of the previous test
            #for now I just focus on mocking export
            mag_order_id = mag_order_model.search(
                self.cr, self.uid,
                [('backend_id', '=', backend_id),
                 ('magento_id', '=', '100000006')])
            mag_order = mag_order_model.browse(self.cr, self.uid, mag_order_id[0])
            comment_id = mail_message_model.create(
                self.cr, self.uid, {
                    'res_id': mag_order.openerp_id.id,
                    'body': 'Test me I famous',
                    'model': 'sale.order',
                    'subtype_id': 1,
                })

            mag_comment_id = mag_comment_model.search(
                self.cr, self.uid,
                [('backend_id', '=', backend_id),
                 ('openerp_id', '=', comment_id)])
            
            export_record(self.session, 'magento.sale.comment', mag_comment_id[0])

            self.assertEqual(len(calls_done), 1)
            
            method, (mag_order_id, state, comment, notification) = calls_done[0]
            self.assertEqual(method, 'sales_order.addComment')
            self.assertEqual(mag_order_id, '100000006')
            self.assertEqual(comment, 'Test me I famous')

