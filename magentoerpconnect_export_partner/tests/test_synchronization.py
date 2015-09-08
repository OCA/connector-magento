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

from openerp.addons.magentoerpconnect.tests.common import (
    mock_api,
)
from openerp.addons.magentoerpconnect.unit.export_synchronizer import (
    export_record)
from .common_partner import SetUpMagentoWithPartner


class TestMagentoPartnerExport(SetUpMagentoWithPartner):
    """ Test the export from a Magento Mock.
    """

    def test_export_partner(self):
        """ Test export of partner"""
        partner_helper = self.get_magento_helper('magento.res.partner')
        address_helper = self.get_magento_helper('magento.address')
        response = {
            'customer.create': partner_helper.get_next_id,
            'customer_address.create': address_helper.get_next_id,
        }
        with mock_api(response, key_func=lambda m, a: m) as calls_done:
            binding_partner_model = self.env['magento.res.partner']
            binding_partner = binding_partner_model.create(
                {'website_id': self.website.id,
                 'openerp_id': self.partner.id,
                 })
            export_record(self.session, 'magento.res.partner',
                          binding_partner.id)
            self.assertEqual(len(calls_done), 3)
            method, [values] = calls_done[0]
            self.assertEqual(method, 'customer.create')
            self.assertEqual(values['email'], 'partner@odoo.com')
            self.assertEqual(values['firstname'], 'Partner')
            self.assertEqual(values['lastname'], 'Partnerbis')

    def test_export_partner_address(self):
        """ Test export of address"""
        partner_helper = self.get_magento_helper('magento.res.partner')
        address_helper = self.get_magento_helper('magento.address')
        response = {
            'customer_address.create': address_helper.get_next_id,
        }
        with mock_api(response, key_func=lambda m, a: m) as calls_done:
            binding_address_model = self.env['magento.address']
            binding_partner_model = self.env['magento.res.partner']
            binding_partner = binding_partner_model.create(
                {'website_id': self.website.id,
                 'openerp_id': self.partner2.id,
                 'magento_id': partner_helper.get_next_id(),
                 })
            binding_address = binding_address_model.create(
                {'magento_partner_id': binding_partner.id,
                 'openerp_id': self.address.id,
                 })
            export_record(self.session, 'magento.address', binding_address.id)

            self.assertEqual(len(calls_done), 1)

            method, [partner, values] = calls_done[0]
            self.assertEqual(method, 'customer_address.create')
            self.assertEqual(values['postcode'], '11112')
            self.assertEqual(values['city'], 'City contact test2')
            self.assertEqual(values['street'], '15, contact test street2')
            self.assertEqual(values['country_id'], 'BE')
            self.assertEqual(values['telephone'], '111111112')
