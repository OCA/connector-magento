# -*- coding: utf-8 -*-
# Copyright 2019 Callino
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


from odoo.addons.component.core import Component
from odoo.addons.connector.unit.mapper import mapping


class ProductCategoryExporter(Component):
    _inherit = 'magento.product.category.exporter'

    def _export_dependencies(self):
        """ Export the dependencies for the record"""
        # Check parent category
        if self.binding.public_categ_id and self.binding.public_categ_id.parent_id and not self.binding.magento_parent_id:
            categ_exporter = self.component(usage='record.exporter', model_name='magento.product.category')
            m_categ = self.env['magento.product.category'].with_context(connector_no_export=True).create({
                'backend_id': self.backend_record.id,
                'public_categ_id': self.binding.public_categ_id.id,
            })
            categ_exporter.run(m_categ)
        super(ProductCategoryExporter, self)._export_dependencies()

    def _has_to_skip(self):
        """ Check if category does have parent category - and if the upper most parent is already in sync"""
        def check_public_parent_recursive(binding):
            parent_binding = binding.public_categ_id.parent_id.magento_bind_ids.filtered(lambda b: b.backend_id == self.backend_record)
            if not parent_binding and not binding.public_categ_id.parent_id.parent_id:
                raise UserWarning('Cannot export the category %s which is not under the main magento category' % binding.name)
            if parent_binding and not binding.public_categ_id.parent_id.parent_id:
                # We are at the magento root category
                return
            check_public_parent_recursive(parent_binding)

        if self.binding.public_categ_id:
            if not self.binding.public_categ_id.parent_id:
                raise UserWarning('Cannot export a root level category to magento')
            check_public_parent_recursive(self.binding)
        else:
            return super(ProductCategoryExporter, self)._has_to_skip()


class ProductCategoryExportMapper(Component):
    _inherit = 'magento.product.category.export.mapper'

    @mapping
    def name(self, record):
        return {
            'name': record.public_categ_id.name
        }
