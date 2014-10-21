# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright 2014
#    Author: Chafique Delli - Akretion
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

from openerp.addons.magentoerpconnect.backend import magento
from openerp.addons.magentoerpconnect_catalog.product_attribute import (
    MagentoAttributeBinder)
#from openerp.addons.magentoerpconnect.unit.backend_adapter import GenericAdapter
from openerp.addons.magentoerpconnect.unit.export_synchronizer import (
    MagentoExporter
)
from openerp.addons.magentoerpconnect.unit.binder import (
    MagentoModelBinder
)
from openerp.addons.magentoerpconnect.connector import get_environment
from openerp.addons.connector.queue.job import job
from openerp.addons.connector.event import on_record_write
from openerp.addons.magentoerpconnect_product_variant import product


@magento(replacing=product.ProductConfigurablePriceExporter)
class ProductConfigurablePriceExporter(product.ProductConfigurablePriceExporter):
    _model_name = ['magento.product.product']

    def _export_super_attribute_price(self, binding):
        """ Export the price of super attribute for the configurable product"""
        for mag_super_attr in binding.mag_super_attr_ids:
            super_attribute_exporter = self.get_connector_unit_for_model(
                MagentoSuperAttributeExporter, 'magento.super.attribute')
            super_attribute_exporter._run(mag_super_attr.id)


@magento
class MagentoSuperAttributeExporter(MagentoExporter):
    _model_name = 'magento.super.attribute'

    def _prepare_data(self, record, dim_value):
        binder = self.get_connector_unit_for_model(MagentoAttributeBinder,
                                                   'magento.attribute.option')
        magento_id = binder.to_backend(dim_value.option_id.id, wrap=True)
        return {
            'value_index': magento_id,
            'is_percent': '0',
            'pricing_value': dim_value.price_extra,
        }

    def _run(self, fields=None):
        if self.binding_record:
            record = self.binding_record
        else:
            record = self.session.browse('magento.super.attribute', fields)

        dimension = record.attribute_id
        mag_product = record.mag_product_display_id

        if not mag_product[dimension.name]:
            domain = [
                ['dimension_id', '=', dimension.id],
                ['product_tmpl_id', '=', mag_product.product_tmpl_id.id]
                ]

            dim_value_ids = self.session.search('dimension.value', domain)

            data = []
            for dim_value in self.session.browse('dimension.value', dim_value_ids):
                data.append(self._prepare_data(record, dim_value))

            super_attribute_adapter = self.get_connector_unit_for_model(
                product.ProductSuperAttributAdapter, 'magento.super.attribute')
            super_attribute_adapter.update(record.magento_id, data)


@magento
class MagentoSuperAttributeBinder(MagentoModelBinder):
    _model_name = 'magento.super.attribute'


@job
def export_dimension_value(session, model_name, magento_super_attr_id, fields=None):
    """ Export dimension value. """
    mag_super_attr = session.browse(model_name, magento_super_attr_id)
    env = get_environment(session, model_name, mag_super_attr.backend_id.id)
    super_attribute_exporter = env.get_connector_unit(
        MagentoSuperAttributeExporter)
    return super_attribute_exporter._run(mag_super_attr.id)


@on_record_write(model_names='dimension.value')
def delay_export_dimension_value_price(session, model_name, record_id, vals=None):
    if 'price_extra' in vals:
        dim_value = session.browse(model_name, record_id)
        binding_magento_super_attr_ids = session.search(
            'magento.super.attribute', [
            ['attribute_id', '=', dim_value.dimension_id.id],
            ['mag_product_display_id.product_tmpl_id', '=', dim_value.product_tmpl_id.id]
            ]
        )
        for binding_magento_super_attr_id in binding_magento_super_attr_ids:
            export_dimension_value.delay(
                session,
                'magento.super.attribute',
                binding_magento_super_attr_id, fields=[record_id])
