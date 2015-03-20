# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2015 Camptocamp SA
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
    import_record)
from .common import mock_api, SetUpMagentoSynchronized
from .data_base import magento_base_responses


class TestPartnerCategory(SetUpMagentoSynchronized):

    def test_import_partner_category(self):
        """ Import of a partner category """
        backend_id = self.backend_id
        with mock_api(magento_base_responses):
            import_record(self.session, 'magento.res.partner.category',
                          backend_id, 2)

        binding_model = self.env['magento.res.partner.category']
        category = binding_model.search([('backend_id', '=', backend_id),
                                         ('magento_id', '=', '2')])
        self.assertEqual(len(category), 1)
        self.assertEqual(category.name, 'Wholesale')
        self.assertEqual(category.tax_class_id, 3)

    def test_import_existing_partner_category(self):
        """ Bind of an existing category with same name"""
        binding_model = self.env['magento.res.partner.category']
        category_model = self.env['res.partner.category']

        existing_category = category_model.create({'name': 'Wholesale'})

        backend_id = self.backend_id
        with mock_api(magento_base_responses):
            import_record(self.session, 'magento.res.partner.category',
                          backend_id, 2)

        category = binding_model.search([('backend_id', '=', backend_id),
                                         ('magento_id', '=', '2')])
        self.assertEqual(len(category), 1)
        self.assertEqual(category.openerp_id, existing_category)
        self.assertEqual(category.name, 'Wholesale')
        self.assertEqual(category.tax_class_id, 3)
