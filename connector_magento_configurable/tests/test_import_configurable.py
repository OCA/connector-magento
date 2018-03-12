# -*- coding: utf-8 -*-
# Copyright 2017 Akretion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from openerp.addons.connector_magento.tests.common import (
    MagentoSyncTestCase,
    recorder,
)


class TestImportConfigurable(MagentoSyncTestCase):

    def setUp(self):
        super(TestImportConfigurable, self).setUp()

    @recorder.use_cassette
    def test_import_product_configurable_links(self):
        """ Import of a configurable product : now we need to import it

        The 'configurable' will be imported and its variants too.
        Then the attributes and the attribute values/lines/prices too
        """
        backend_id = self.backend.id

        self.env['magento.product.template'].import_record(
            self.backend, '408'
        )

        template_model = self.env['magento.product.template']
        templates = template_model.search([('backend_id', '=', backend_id),
                                           ('external_id', '=', '408')])
        self.assertEqual(len(templates), 1)

        # the configurable importer takes a magento.product.product
        # as parameter instead of an sku
        self.env['magento.product.template'].import_record(
            self.backend, templates
        )

        tmpl_id = templates[0].id
        variants = template_model.search([('backend_id', '=', backend_id),
                                         ('product_tmpl_id', '=', tmpl_id)])
        self.assertEqual(len(variants), 15)

        line_model = self.env['product.attribute.line']
        lines = line_model.search([('product_tmpl_id', '=', tmpl_id)])
        self.assertEqual(len(lines), 2)  # 2 attributes for the template

        attribute_ids = [lines[0].attribute_id.id, lines[1].attribute_id.id]
        attribute_model = self.env['magento.product.attribute']
        attributes = attribute_model.search([('backend_id', '=', backend_id),
                                             ('odoo_id', 'in', attribute_ids)])
        self.assertEqual(len(attributes), 2)  # color and size

        value_model = self.env['magento.product.attribute.value']
        values = value_model.search([('backend_id', '=', backend_id),
                                     ('attribute_id', 'in', attribute_ids)])
        self.assertEqual(len(values), 8)  # Blue, White, Black, S, M, L, XS, XL

        price_model = self.env['magento.product.attribute.price']
        prices = price_model.search([('backend_id', '=', backend_id)])
        self.assertEqual(len(prices), len(values))
