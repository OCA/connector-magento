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

from openerp.addons.magentoerpconnect.unit.import_synchronizer import (
    import_batch,
    import_record)
from openerp.addons.connector.session import ConnectorSession
import openerp.tests.common as common
from .common import mock_api
from .test_data import magento_base_responses
from .test_data_address_book import (no_address,
                                     individual_1_address,
                                     individual_2_addresses,
                                     company_1_address,
                                     company_2_addresses)

DB = common.DB
ADMIN_USER_ID = common.ADMIN_USER_ID


class test_import_address_book(common.SingleTransactionCase):
    """ Test the imports of the address book from a Magento Mock.
    """

    def setUp(self):
        super(test_import_address_book, self).setUp()
        self.backend_model = self.registry('magento.backend')
        self.session = ConnectorSession(self.cr, self.uid)
        self.session.context['__test_no_commit'] = True
        self.model = self.registry('magento.res.partner')
        self.address_model = self.registry('magento.address')
        backend_ids = self.backend_model.search(
            self.cr, self.uid,
            [('name', '=', 'Test Magento Address book')])
        if backend_ids:
            self.backend_id = backend_ids[0]
        else:
            data_obj = self.registry('ir.model.data')
            warehouse_id = data_obj.get_object_reference(
                self.cr, self.uid, 'stock', 'warehouse0')[1]
            self.backend_id = self.backend_model.create(
                self.cr,
                self.uid,
                {'name': 'Test Magento Address book',
                 'version': '1.7',
                 'location': 'http://anyurl',
                 'username': 'guewen',
                 'warehouse_id': warehouse_id,
                 'password': '42'})

    def test_00_setup(self):
        """ Import the informations required for the customers """
        with mock_api(magento_base_responses):
            import_batch(self.session, 'magento.website', self.backend_id)
            import_batch(self.session, 'magento.store', self.backend_id)
            import_batch(self.session, 'magento.storeview', self.backend_id)
            import_record(self.session, 'magento.res.partner.category',
                          self.backend_id, 1)

    def test_10_no_address(self):
        """ Import an account without any address"""
        with mock_api(no_address):
            import_record(self.session, 'magento.res.partner',
                          self.backend_id, '9999253')
        cr, uid = self.cr, self.uid
        partner_ids = self.model.search(cr, uid,
                                        [('magento_id', '=', '9999253'),
                                         ('backend_id', '=', self.backend_id)])
        self.assertEqual(len(partner_ids), 1)
        partner = self.model.browse(cr, uid, partner_ids[0])
        self.assertEqual(partner.name, 'Benjamin Le Goff')
        self.assertEqual(partner.type, 'default')
        self.assertEqual(len(partner.child_ids), 0)

    def test_11_individual_1_address(self):
        """ Import an individual (b2c) with 1 billing address """
        with mock_api(individual_1_address):
            import_record(self.session, 'magento.res.partner',
                          self.backend_id, '9999254')
        cr, uid = self.cr, self.uid
        partner_ids = self.model.search(cr, uid,
                                        [('magento_id', '=', '9999254'),
                                         ('backend_id', '=', self.backend_id)])
        self.assertEqual(len(partner_ids), 1)
        partner = self.model.browse(cr, uid, partner_ids[0])
        # Name of the billing address
        self.assertEqual(partner.name, 'Ferreira Margaux')
        self.assertEqual(partner.type, 'default')
        # billing address merged with the partner
        self.assertEqual(len(partner.child_ids), 0)
        self.assertEqual(len(partner.magento_bind_ids), 1)
        self.assertEqual(len(partner.magento_address_bind_ids), 1)
        address_bind = partner.magento_address_bind_ids[0]
        self.assertEqual(address_bind.magento_id, '9999253',
                         msg="The merged address should be the "
                             "billing address")

    def test_12_individual_2_addresses(self):
        """ Import an individual (b2c) with 2 addresses """
        with mock_api(individual_2_addresses):
            import_record(self.session, 'magento.res.partner',
                          self.backend_id, '9999255')
        cr, uid = self.cr, self.uid
        partner_ids = self.model.search(cr, uid,
                                        [('magento_id', '=', '9999255'),
                                         ('backend_id', '=', self.backend_id)])
        self.assertEqual(len(partner_ids), 1)
        partner = self.model.browse(cr, uid, partner_ids[0])
        # Name of the billing address
        self.assertEqual(partner.name, u'Mace Sébastien')
        self.assertEqual(partner.type, 'default')
        # billing address merged with the partner,
        # second address as a contact
        self.assertEqual(len(partner.child_ids), 1)
        self.assertEqual(len(partner.magento_bind_ids), 1)
        self.assertEqual(len(partner.magento_address_bind_ids), 1)
        address_bind = partner.magento_address_bind_ids[0]
        self.assertEqual(address_bind.magento_id, '9999254',
                         msg="The merged address should be the "
                             "billing address")
        self.assertEqual(partner.child_ids[0].type, 'delivery',
                         msg="The shipping address should be of "
                             "type 'delivery'")

    def test_13_company_1_address(self):
        """ Import an company (b2b) with 1 address """
        with mock_api(company_1_address):
            import_record(self.session, 'magento.res.partner',
                          self.backend_id, '9999256')
        cr, uid = self.cr, self.uid
        partner_ids = self.model.search(cr, uid,
                                        [('magento_id', '=', '9999256'),
                                         ('backend_id', '=', self.backend_id)])
        self.assertEqual(len(partner_ids), 1)
        partner = self.model.browse(cr, uid, partner_ids[0])
        # Company of the billing address
        self.assertEqual(partner.name, 'Marechal')
        self.assertEqual(partner.type, 'default')
        # all addresses as contacts
        self.assertEqual(len(partner.child_ids), 1)
        self.assertEqual(len(partner.magento_bind_ids), 1)
        self.assertEqual(len(partner.magento_address_bind_ids), 0)
        self.assertEqual(partner.child_ids[0].type, 'invoice',
                         msg="The billing address should be of "
                             "type 'invoice'")

    def test_14_company_2_addresses(self):
        """ Import an company (b2b) with 2 addresses """
        with mock_api(company_2_addresses):
            import_record(self.session, 'magento.res.partner',
                          self.backend_id, '9999257')
        cr, uid = self.cr, self.uid
        partner_ids = self.model.search(cr, uid,
                                        [('magento_id', '=', '9999257'),
                                         ('backend_id', '=', self.backend_id)])
        self.assertEqual(len(partner_ids), 1)
        partner = self.model.browse(cr, uid, partner_ids[0])
        # Company of the billing address
        self.assertEqual(partner.name, 'Bertin')
        self.assertEqual(partner.type, 'default')
        # all addresses as contacts
        self.assertEqual(len(partner.child_ids), 2)
        self.assertEqual(len(partner.magento_bind_ids), 1)
        self.assertEqual(len(partner.magento_address_bind_ids), 0)

        def get_address(magento_id):
            address_ids = self.address_model.search(
                cr, uid,
                [('magento_id', '=', magento_id),
                 ('backend_id', '=', self.backend_id)])
            self.assertEqual(len(address_ids), 1)
            return self.address_model.browse(cr, uid, address_ids[0])
        # billing address
        address = get_address('9999257')
        self.assertEqual(address.type, 'invoice',
                         msg="The billing address should be of "
                             "type 'invoice'")
        # shipping address
        address = get_address('9999258')
        self.assertEqual(address.type, 'delivery',
                         msg="The shipping address should be of "
                             "type 'delivery'")
