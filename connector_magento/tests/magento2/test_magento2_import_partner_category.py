# Copyright 2015-2019 Camptocamp SA
# Copyright 2020 Opener B.V.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from .common import Magento2SyncTestCase, recorder


class TestImportPartnerCategory(Magento2SyncTestCase):

    @recorder.use_cassette
    def test_import_partner_category(self):
        """ Import of a partner category """
        self.env['magento.res.partner.category'].import_record(
            self.backend, 2
        )

        backend_id = self.backend.id
        binding_model = self.env['magento.res.partner.category']
        category = binding_model.search([('backend_id', '=', backend_id),
                                         ('external_id', '=', '2')])
        self.assertEqual(len(category), 1)
        self.assertEqual(category.name, 'Wholesale')
        self.assertEqual(category.tax_class_id, 3)

    @recorder.use_cassette
    def test_import_existing_partner_category(self):
        """ Bind of an existing category with same name"""
        binding_model = self.env['magento.res.partner.category']
        category_model = self.env['res.partner.category']

        existing_category = category_model.create({'name': 'Wholesale'})

        self.env['magento.res.partner.category'].import_record(
            self.backend, 2
        )

        backend_id = self.backend.id
        category = binding_model.search([('backend_id', '=', backend_id),
                                         ('external_id', '=', '2')])
        self.assertEqual(len(category), 1)
        self.assertEqual(category.odoo_id, existing_category)
        self.assertEqual(category.name, 'Wholesale')
        self.assertEqual(category.tax_class_id, 3)
