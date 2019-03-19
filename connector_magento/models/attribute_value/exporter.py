# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import Component
from odoo.addons.connector.unit.mapper import mapping, only_create
from slugify import slugify


class ProductAttributeValueDefinitionExporter(Component):
    _name = 'magento.product.attribute.value.exporter'
    _inherit = 'magento.exporter'
    _apply_on = ['magento.product.attribute.value']

    def _should_import(self):
        return False


class MagentoProductAttributeValueExportMapper(Component):
    _name = 'magento.product.attribute.value.export.mapper'
    _inherit = 'magento.export.mapper'
    _apply_on = ['magento.product.attribute.value']

    direct = [
        ('name', 'label'),
    ]

    @mapping
    def is_default(self, record):
        return {'is_default': False}

    @mapping
    def code_value(self, record):
        # Only set value as member if already set - so we can update - else it is a create !
        if record.code:
            return {'value': record.code}

    @mapping
    def sort_order(self, record):
        return {'sort_order': record.sequence if record.sequence else 0}


class MagentoProductAttributeValueMapChild(Component):
    _name = 'magento.product.attribute.value.map.child.export'
    _inherit = 'base.map.child.export'
    _apply_on = ['magento.product.attribute.value']

    def skip_item(self, map_record):
        """ Hook to implement in sub-classes when some child
        records should be skipped.

        The parent record is accessible in ``map_record``.
        If it returns True, the current child record is skipped.

        :param map_record: record that we are converting
        :type map_record: :py:class:`MapRecord`
        """
        return True if not map_record.source.code else False


'''
class ProductAttributeValueExportMapper(Component):
    _name = 'product.attribute.value.export.mapper'
    _inherit = 'magento.export.mapper'
    _apply_on = ['product.attribute.value']

    direct = [
        ('name', 'label'),
    ]

    @mapping
    def code(self, record):
        return {'code': "%s_%s" % (slugify(record['name']), record.id, )}

    @mapping
    def attributeCode(self, record):
        return {'attributeCode': 'asdf'}
'''