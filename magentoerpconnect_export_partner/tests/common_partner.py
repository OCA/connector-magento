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


class SetUpMagentoWithPartner(SetUpMagentoSynchronized):

    def setUp(self):
        super(SetUpMagentoWithPartner, self).setUp()
        self.website = self.env['magento.website'].search(
            [('backend_id', '=', self.backend_id)],
            limit=1,
        )
        partner_model = self.env['res.partner']
        belgium = self.env['res.country'].search(
            [('code', '=', 'BE')],
            limit=1,
        )
        self.partner = partner_model.create(
            {'name': 'Partner Partnerbis',
             'is_company': True,
             'email': 'partner@odoo.com',
             'street': '15, test street',
             'phone': '0000000000',
             'zip': '00000',
             'country_id': belgium.id,
             'city': 'City test'})
        self.contact = partner_model.create(
            {'name': 'Contact',
             'parent_id': self.partner.id,
             'street': '15, contact test street',
             'phone': '111111111',
             'zip': '11111',
             'country_id': belgium.id,
             'city': 'City contact test'})

        self.partner2 = partner_model.create(
            {'name': 'Partner2 Partner2bis',
             'is_company': True,
             'email': 'partner2@odoo.com'})
        self.address = partner_model.create(
            {'name': 'Contact address2',
             'parent_id': self.partner2.id,
             'street': '15, contact test street2',
             'phone': '111111112',
             'zip': '11112',
             'country_id': belgium.id,
             'city': 'City contact test2'})
