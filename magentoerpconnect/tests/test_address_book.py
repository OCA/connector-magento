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
from .data_base import magento_base_responses
from .data_address_book import (no_address,
                                individual_1_address,
                                individual_2_addresses,
                                company_1_address,
                                company_2_addresses)

DB = common.DB
ADMIN_USER_ID = common.ADMIN_USER_ID


class TestImportAddressBook(common.TransactionCase):
    """ Test the imports of the address book from a Magento Mock.
    """

    def setUp(self):
        super(TestImportAddressBook, self).setUp()
        self.backend_model = self.env['magento.backend']
        self.session = ConnectorSession(self.env.cr, self.env.uid,
                                        context=self.env.context)
        self.model = self.env['magento.res.partner']
        self.address_model = self.env['magento.address']
        warehouse_id = self.env.ref('stock.warehouse0').id
        self.backend_id = self.backend_model.create({
            'name': 'Test Magento Address book',
            'version': '1.7',
            'location': 'http://anyurl',
            'username': 'guewen',
            'warehouse_id': warehouse_id,
            'password': '42'}).id
        with mock_api(magento_base_responses):
            import_batch(self.session, 'magento.website', self.backend_id)
            import_batch(self.session, 'magento.store', self.backend_id)
            import_batch(self.session, 'magento.storeview', self.backend_id)
            import_record(self.session, 'magento.res.partner.category',
                          self.backend_id, 1)

    def test_no_address(self):
        """ Import an account without any address """
        with mock_api(no_address):
            import_record(self.session, 'magento.res.partner',
                          self.backend_id, '9999253')
        partner = self.model.search([('magento_id', '=', '9999253'),
                                     ('backend_id', '=', self.backend_id)])
        self.assertEqual(len(partner), 1)
        self.assertEqual(partner.name, 'Benjamin Le Goff')
        self.assertEqual(partner.type, 'default')
        self.assertEqual(len(partner.child_ids), 0)

    def test_individual_1_address(self):
        """ Import an individual (b2c) with 1 billing address """
        with mock_api(individual_1_address):
            import_record(self.session, 'magento.res.partner',
                          self.backend_id, '9999254')
        partner = self.model.search([('magento_id', '=', '9999254'),
                                     ('backend_id', '=', self.backend_id)])
        self.assertEqual(len(partner), 1)
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

    def test_individual_2_addresses(self):
        """ Import an individual (b2c) with 2 addresses """
        with mock_api(individual_2_addresses):
            import_record(self.session, 'magento.res.partner',
                          self.backend_id, '9999255')
        partner = self.model.search([('magento_id', '=', '9999255'),
                                     ('backend_id', '=', self.backend_id)])
        self.assertEqual(len(partner), 1)
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

    def test_company_1_address(self):
        """ Import an company (b2b) with 1 address """
        with mock_api(company_1_address):
            import_record(self.session, 'magento.res.partner',
                          self.backend_id, '9999256')
        partner = self.model.search([('magento_id', '=', '9999256'),
                                     ('backend_id', '=', self.backend_id)])
        self.assertEqual(len(partner), 1)
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

    def test_company_2_addresses(self):
        """ Import an company (b2b) with 2 addresses """
        with mock_api(company_2_addresses):
            import_record(self.session, 'magento.res.partner',
                          self.backend_id, '9999257')
        partner = self.model.search([('magento_id', '=', '9999257'),
                                     ('backend_id', '=', self.backend_id)])
        self.assertEqual(len(partner), 1)
        # Company of the billing address
        self.assertEqual(partner.name, 'Bertin')
        self.assertEqual(partner.type, 'default')
        # all addresses as contacts
        self.assertEqual(len(partner.child_ids), 2)
        self.assertEqual(len(partner.magento_bind_ids), 1)
        self.assertEqual(len(partner.magento_address_bind_ids), 0)

        def get_address(magento_id):
            address = self.address_model.search(
                [('magento_id', '=', magento_id),
                 ('backend_id', '=', self.backend_id)])
            self.assertEqual(len(address), 1)
            return address
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
