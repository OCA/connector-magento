# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Florian da Costa
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
from openerp.addons.magentoerpconnect.tests.common import (
    mock_api,
)
from openerp.addons.magentoerpconnect.unit.export_synchronizer import (
    export_record)


class SetUpMagentoWithPartner(SetUpMagentoSynchronized):

    def setUp(self):
        super(SetUpMagentoWithPartner, self).setUp()
        cr = self.cr
        uid = self.uid
        self.website_id = self.registry('magento.website').search(cr, uid, [
            ('backend_id', '=', self.backend_id)])[0]
        oe_partner_model = self.registry('res.partner')
        country_id = self.registry('res.country').search(cr, uid, [
            ('code', '=', 'BE')])[0]
        self.partner_id = oe_partner_model.create(
            cr, uid,
            {'name': 'Partner Partner2',
             'is_company': True,
             'email': 'partner@odoo.com',
             'street': '15, test street',
             'phone': '0000000000',
             'zip': '00000',
             'country_id': country_id,
             'city': 'City test'})
        self.contact_id = oe_partner_model.create(
            cr, uid,
            {'name': 'Contact',
             'parent_id': self.partner_id,
             'street': '15, contact test street',
             'phone': '111111111',
             'zip': '11111',
             'country_id': country_id,
             'city': 'City contact test'})


class TestMagentoPartnerExport(SetUpMagentoWithPartner):
    """ Test the export from a Magento Mock.
    """

    def test_1_export_partner(self):
        """ Test export of partner"""
        response = {
            'customer.create': 1,
        }
        cr = self.cr
        uid = self.uid
        with mock_api(response, key_func=lambda m, a: m) as calls_done:
            mag_address_model = self.registry('magento.address')
            mag_partner_model = self.registry('magento.res.partner')
            mag_partner_id = mag_partner_model.create(cr, uid, {
                'website_id': self.website_id,
                'openerp_id': self.partner_id,
                })
            export_record(self.session, 'magento.res.partner', mag_partner_id)
            self.assertEqual(len(calls_done), 1)
            method, [values] = calls_done[0]
            self.assertEqual(method, 'customer.create')
            self.assertEqual(values['email'], 'partner@odoo.com')
            self.assertEqual(values['firstname'], 'Partner')
            self.assertEqual(values['lastname'], 'Partner2')

            mag_address_ids = mag_address_model.search(cr, uid, [
                ('magento_partner_id', '=', mag_partner_id)])
            self.assertEqual(len(mag_address_ids), 2)

    def test_2_export_partner_address(self):
        """ Test export of address"""
        response = {
            'customer_address.create': 2,
        }
        cr = self.cr
        uid = self.uid
        with mock_api(response, key_func=lambda m, a: m) as calls_done:
            mag_address_model = self.registry('magento.address')
            mag_partner_model = self.registry('magento.res.partner')
            mag_partner_id = mag_partner_model.create(cr, uid, {
                'website_id': self.website_id,
                'openerp_id': self.partner_id,
                'magento_id': 1,
                })
            mag_address_id = mag_address_model.create(cr, uid, {
                'magento_partner_id': mag_partner_id,
                'openerp_id': self.partner_id,
                })
            export_record(self.session, 'magento.address', mag_address_id)

            self.assertEqual(len(calls_done), 1)

            method, [partner, values] = calls_done[0]
            self.assertEqual(method, 'customer_address.create')
            self.assertEqual(partner, 1)
            self.assertEqual(values['postcode'], '00000')
            self.assertEqual(values['city'], 'City test')
            self.assertEqual(values['street'], '15, test street')
            self.assertEqual(values['country_id'], 'BE')
            self.assertEqual(values['telephone'], '0000000000')
