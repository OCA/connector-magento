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

from openerp.addons.magentoerpconnect.tests.test_synchronization import (
    SetUpMagentoSynchronized)
from openerp.addons.magentoerpconnect.tests.test_data import (
    magento_base_responses)
from openerp.addons.magentoerpconnect.unit.import_synchronizer import (
    import_record)
from openerp.addons.magentoerpconnect.tests.common import (
    mock_api,
    mock_urlopen_image)
from openerp.addons.magentoerpconnect.unit.export_synchronizer import (
    export_record)


class TestMagentoSaleCommentImport(SetUpMagentoSynchronized):
    """ Test the imports from a Magento Mock.

    The data returned by Magento are those created for the
    demo version of Magento on a standard 1.7 version.
    """

    def test_10_import_sale_comment(self):
        """ Test import of sale order comment"""
        cr = self.cr
        uid = self.uid
        backend_id = self.backend_id
        with mock_api(magento_base_responses):
            with mock_urlopen_image():
                import_record(self.session,
                              'magento.sale.order',
                              backend_id, 900000695)
                order_model = self.registry('magento.sale.order')
        mag_order_ids = order_model.search(cr, uid, [
            ('backend_id', '=', backend_id),
            ('magento_id', '=', '900000695'),
            ])
        self.assertEqual(len(mag_order_ids), 1)

        order = order_model.read(cr, uid, mag_order_ids[0], ['openerp_id'])
        order_id = order['openerp_id'][0]
        comment_ids = self.registry('magento.sale.comment').search(cr, uid, [
            ('backend_id', '=', backend_id),
            ('res_id', '=', order_id)
            ])
        self.assertEqual(len(comment_ids), 2)


class SetUpMagentoWithSaleOrder(SetUpMagentoSynchronized):

    def setUp(self):
        super(SetUpMagentoWithSaleOrder, self).setUp()
        cr = self.cr
        uid = self.uid
        mag_order_model = self.registry('magento.sale.order')
        with mock_api(magento_base_responses):
            with mock_urlopen_image():
                import_record(self.session,
                              'magento.sale.order',
                              self.backend_id, 900000691)

        mag_order_ids = mag_order_model.search(cr, uid, [
            ('backend_id', '=', self.backend_id),
            ('magento_id', '=', '900000691'),
            ])

        self.mag_order = mag_order_model.browse(cr, uid, mag_order_ids[0])


class TestMagentoMoveComment(SetUpMagentoWithSaleOrder):

    def test_10_import_sale_comment_for_edited_sale_order(self):
        """ Test import of sale order comment for edited sale order
        Note: the parent have been note cancel in the magento_base_response
        because we want to import the both sale order.
        """
        cr = self.cr
        uid = self.uid
        backend_id = self.backend_id
        with mock_api(magento_base_responses):
            with mock_urlopen_image():
                import_record(self.session,
                              'magento.sale.order',
                              backend_id, '900000691-1')
                order_model = self.registry('magento.sale.order')
        mag_order_ids = order_model.search(cr, uid, [
            ('backend_id', '=', backend_id),
            ('magento_id', '=', '900000691-1'),
            ])
        self.assertEqual(len(mag_order_ids), 1)

        order = order_model.read(cr, uid, mag_order_ids[0], ['openerp_id'])
        order_id = order['openerp_id'][0]

        comment_ids = self.registry('magento.sale.comment').search(cr, uid, [
            ('backend_id', '=', backend_id),
            ('res_id', '=', order_id),
            ])
        # The sale order 900000691 have 1 comment
        # and the 900000691-1 have 2 comment
        # Total is 3 comment
        self.assertEqual(len(comment_ids), 3)


class TestMagentoSaleCommentExport(SetUpMagentoWithSaleOrder):
    """ Test the imports from a Magento Mock.

    The data returned by Magento are those created for the
    demo version of Magento on a standard 1.7 version.
    """

    def test_20_export_sale_comment(self):
        """ Test export of sale order comment"""
        response = {
            'sales_order.addComment': True,
        }
        cr = self.cr
        uid = self.uid
        with mock_api(response, key_func=lambda m, a: m) as calls_done:
            mag_comment_model = self.registry('magento.sale.comment')
            mail_message_model = self.registry('mail.message')

            comment_id = mail_message_model.create(cr, uid, {
                'res_id': self.mag_order.openerp_id.id,
                'body': 'Test me I famous',
                'model': 'sale.order',
                'subtype_id': 1,
                })

            mag_comment_id = mag_comment_model.search(cr, uid, [
                ('backend_id', '=', self.backend_id),
                ('openerp_id', '=', comment_id),
                ])[0]

            export_record(self.session, 'magento.sale.comment', mag_comment_id)

            self.assertEqual(len(calls_done), 1)

            method, (mag_order_id, state, comment, notif) = calls_done[0]
            self.assertEqual(method, 'sales_order.addComment')
            self.assertEqual(mag_order_id, '900000691')
            # the comment is in <p> so BeautifulSoup adds a final \n
            self.assertEqual(comment.rstrip('\n'), 'Test me I famous')
