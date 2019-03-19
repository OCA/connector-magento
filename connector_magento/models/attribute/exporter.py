# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)
from odoo.addons.component.core import Component
from odoo.addons.connector.unit.mapper import mapping, only_create


class ProductAttributeDefinitionExporter(Component):
    _name = 'magento.product.attribute.exporter'
    _inherit = 'magento.exporter'
    _apply_on = ['magento.product.attribute']

    def _should_import(self):
        return False

    '''
    Does not work as expected - because we don't get back the value from magento on option add call !
    def _after_export(self):
        # Here we do check for not exported attribute values - and we do export them
        exported_ids = [mvalue.odoo_id.id for mvalue in self.binding.magento_attribute_value_ids]
        export_values = self.binding.value_ids.filtered(lambda v: v.id not in exported_ids)
        for value in export_values:
            self._export_dependency(value, 'magento.product.attribute.value', binding_extra_vals={
                'magento_attribute_id': self.binding.id
            })
    '''

class ProductAttributeExportMapper(Component):
    _name = 'magento.product.attribute.export.mapper'
    _inherit = 'magento.export.mapper'
    _apply_on = ['magento.product.attribute']

    children = [
        ('magento_attribute_value_ids', 'options', 'magento.product.attribute.value'),
    ]

    '''
    No Support for translatable currently on export !
    translatable = [
        ('name', 'default_frontend_label')
    ]
    '''

    direct = [
        ('name', 'default_frontend_label'),
        ('frontend_input', 'frontend_input'),
        ('attribute_code', 'attribute_code')
    ]

    @mapping
    def attribute_id(self, record):
        # On create we do not supply anything here - on update we need the id
        if record.external_id:
            return {'attribute_id': int(record.external_id)}
