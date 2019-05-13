# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)
from odoo import fields, tools
from odoo.addons.component.core import Component
from odoo.addons.connector.unit.mapper import mapping, only_create


class ProductAttributeDefinitionExporter(Component):
    _name = 'magento.product.attribute.exporter'
    _inherit = 'magento.exporter'
    _apply_on = ['magento.product.attribute']

    def _should_import(self):
        return False

    def _update_binding_record_after_create(self, data):
        # Do use the importer to update the binding
        importer = self.component(usage='record.importer',
                                model_name='magento.product.attribute')
        importer.run(data, force=True, binding=self.binding)
        self.external_id = data['attribute_id']

    def _update_attribute_with_result(self, result):
        ov_binder = self.binder_for(model='magento.product.attribute.value')
        now_fmt = fields.Datetime.now()
        # Here we have to go over the options - and update the value on our side - the value is the id generated by magento
        for option in result['options']:
            if not option['value']:
                continue
            option_binding = self.binding.magento_attribute_value_ids.filtered(lambda b: b.name == option['label'])
            assert(len(option_binding) <= 1)
            if option_binding:
                option_binding.with_context(connector_no_export=True).write({
                    'code': option['value'],
                    'external_id': "%s_%s" % (str(result['attribute_id']), tools.ustr(option['value'])),
                })
            else:
                # No existing binding - so we have to create a new binding
                odoo_option = self.binding.value_ids.filtered(lambda b: b.name == option['label'])
                assert(len(odoo_option) <= 1)
                if odoo_option:
                    # Create binding here
                    external_id = "%s_%s" % (str(result['attribute_id']), tools.ustr(option['value']))
                    ov_binder.model.create({
                        ov_binder._external_field: external_id,
                        ov_binder._sync_date_field: now_fmt,
                        ov_binder._odoo_field: odoo_option.id,
                        ov_binder._backend_field: self.backend_record.id,
                        'magento_attribute_id': self.binding.id,
                        'code': tools.ustr(option['value'])
                    })

    '''
    We do overwrite the _create - because we need to analyze the result
    '''
    def _create(self, data):
        """ Create the Magento record """
        # special check on data before export
        self._validate_create_data(data)
        result = self.backend_adapter.create(data, binding=self.binding)
        self._update_attribute_with_result(result)
        return result

    def _update(self, data, storeview_code=None):
        result = super(ProductAttributeDefinitionExporter, self)._update(data, storeview_code)
        self._update_attribute_with_result(result)
        return result

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

    @mapping
    def value_options(self, record):
        mids = []
        mapped = []
        mvalue_mapper = self.component(
            usage='export.mapper',
            model_name='magento.product.attribute.value'
        )
        value_mapper = self.component(
            usage='export.mapper',
            model_name='product.attribute.value'
        )

        for mvalue in record.magento_attribute_value_ids:
            map_record = mvalue_mapper.map_record(mvalue, parent=record)
            mids.append(mvalue.odoo_id.id)
            mapped.append(map_record.values())
        if self.backend_record.export_all_options:
            for value in record.value_ids.filtered(lambda v: v.id not in mids):
                map_record = value_mapper.map_record(value, parent=record)
                mapped.append(map_record.values())
        return {'options': mapped}
