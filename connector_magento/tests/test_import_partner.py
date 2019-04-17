# Copyright 2015-2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from .common import MagentoSyncTestCase, recorder


class TestImportPartner(MagentoSyncTestCase):

    def setUp(self):
        super(TestImportPartner, self).setUp()
        category_model = self.env['res.partner.category']
        existing_category = category_model.create({'name': 'General'})
        self.create_binding_no_export(
            'magento.res.partner.category',
            existing_category,
            1
        )
        self.model = self.env['magento.res.partner']
        self.address_model = self.env['magento.address']

    @recorder.use_cassette
    def test_import_partner_no_address(self):
        """ Import an partner account without any address """
        self.env['magento.res.partner'].import_record(self.backend, '139')

        partner = self.model.search([('external_id', '=', '139'),
                                     ('backend_id', '=', self.backend.id)])
        self.assertEqual(len(partner), 1)
        self.assertEqual(partner.name, 'Benjamin Le Goff')
        self.assertEqual(partner.type, 'contact')
        self.assertEqual(len(partner.child_ids), 0)

    @recorder.use_cassette
    def test_import_partner_individual_1_address(self):
        """ Import an individual (b2c) with 1 billing address

        A magento customer is considered an individual if its billing
        address has an empty 'company' field
        """
        self.env['magento.res.partner'].import_record(self.backend, '136')
        partner = self.model.search([('external_id', '=', '136'),
                                     ('backend_id', '=', self.backend.id)])
        self.assertEqual(len(partner), 1)
        # Name of the billing address
        self.assertEqual(partner.name, 'Jane Doe')
        self.assertEqual(partner.type, 'contact')
        # billing address merged with the partner
        self.assertEqual(len(partner.child_ids), 0)
        self.assertEqual(len(partner.magento_bind_ids), 1)
        self.assertEqual(len(partner.magento_address_bind_ids), 1)
        address_bind = partner.magento_address_bind_ids[0]
        self.assertEqual(address_bind.external_id, '92',
                         msg="The merged address should be the "
                             "billing address")
        self.assertEqual(partner.company_id.id,
                         self.backend.warehouse_id.company_id.id)

    @recorder.use_cassette
    def test_import_partner_individual_2_addresses(self):
        """ Import an individual (b2c) with 2 addresses

        A magento customer is considered an individual if its billing
        address has an empty 'company' field
        """
        self.env['magento.res.partner'].import_record(self.backend, '65')

        partner = self.model.search([('external_id', '=', '65'),
                                     ('backend_id', '=', self.backend.id)])
        self.assertEqual(len(partner), 1)
        # Name of the billing address
        self.assertEqual(partner.name, 'Tay Ray')
        self.assertEqual(partner.type, 'contact')
        # billing address merged with the partner,
        # second address as a contact
        self.assertEqual(len(partner.child_ids), 1)
        self.assertEqual(len(partner.magento_bind_ids), 1)
        self.assertEqual(len(partner.magento_address_bind_ids), 1)
        address_bind = partner.magento_address_bind_ids[0]
        self.assertEqual(address_bind.external_id, '35',
                         msg="The merged address should be the "
                             "billing address")
        self.assertEqual(partner.child_ids[0].type, 'delivery',
                         msg="The shipping address should be of "
                             "type 'delivery'")
        self.assertEqual(partner.company_id.id,
                         self.backend.company_id.id)
        self.assertEqual(partner.child_ids[0].company_id.id,
                         self.backend.company_id.id)

    @recorder.use_cassette
    def test_import_partner_company_1_address(self):
        """ Import an company (b2b) with 1 address

        A magento customer is considered a company if its billing
        address contains something in the 'company' field
        """
        self.env['magento.res.partner'].import_record(self.backend, '104')

        partner = self.model.search([('external_id', '=', '104'),
                                     ('backend_id', '=', self.backend.id)])
        self.assertEqual(len(partner), 1)
        # Company of the billing address
        self.assertEqual(partner.name, 'Drew France')
        self.assertEqual(partner.type, 'contact')
        # all addresses as contacts
        self.assertEqual(len(partner.child_ids), 1)
        self.assertEqual(len(partner.magento_bind_ids), 1)
        self.assertEqual(len(partner.magento_address_bind_ids), 0)
        self.assertEqual(partner.child_ids[0].type, 'invoice',
                         msg="The billing address should be of "
                             "type 'invoice'")

    @recorder.use_cassette
    def test_import_partner_company_2_addresses(self):
        """ Import an company (b2b) with 2 addresses

        A magento customer is considered a company if its billing
        address contains something in the 'company' field
        """
        self.env['magento.res.partner'].import_record(self.backend, '99')

        partner = self.model.search([('external_id', '=', '99'),
                                     ('backend_id', '=', self.backend.id)])
        self.assertEqual(len(partner), 1)
        # Company of the billing address
        self.assertEqual(partner.name, 'Clay Lock')
        self.assertEqual(partner.type, 'contact')
        # all addresses as contacts
        self.assertEqual(len(partner.child_ids), 2)
        self.assertEqual(len(partner.magento_bind_ids), 1)
        self.assertEqual(len(partner.magento_address_bind_ids), 0)

        def get_address(external_id):
            address = self.address_model.search(
                [('external_id', '=', external_id),
                 ('backend_id', '=', self.backend.id)])
            self.assertEqual(len(address), 1)
            return address
        # billing address
        address = get_address('68')
        self.assertEqual(address.type, 'invoice',
                         msg="The billing address should be of "
                             "type 'invoice'")
        # shipping address
        address = get_address('98')
        self.assertEqual(address.type, 'delivery',
                         msg="The shipping address should be of "
                             "type 'delivery'")

    @recorder.use_cassette('test_import_partner_individual_2_addresses')
    def test_import_partner_individual_2_addresses_multi_company(self):
        """Import an invidual on multi backend company"""
        self.backend.is_multi_company = True
        self.env['magento.res.partner'].import_record(self.backend, '65')

        partner = self.model.search([('external_id', '=', '65'),
                                     ('backend_id', '=', self.backend.id)])
        self.assertEqual(len(partner), 1)
        # Name of the billing address
        self.assertEqual(partner.name, 'Tay Ray')
        self.assertEqual(partner.type, 'contact')
        # billing address merged with the partner,
        # second address as a contact
        self.assertEqual(len(partner.child_ids), 1)
        self.assertEqual(len(partner.magento_bind_ids), 1)
        self.assertEqual(len(partner.magento_address_bind_ids), 1)
        address_bind = partner.magento_address_bind_ids[0]
        self.assertEqual(address_bind.external_id, '35',
                         msg="The merged address should be the "
                             "billing address")
        self.assertEqual(partner.child_ids[0].type, 'delivery',
                         msg="The shipping address should be of "
                             "type 'delivery'")
        self.assertFalse(partner.company_id.id)
        self.assertFalse(partner.child_ids[0].company_id.id)
