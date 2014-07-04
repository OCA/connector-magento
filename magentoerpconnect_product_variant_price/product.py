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
from openerp.addons.connector.unit.mapper import mapping
from openerp.addons.magentoerpconnect_product_variant import product
from openerp.addons.magentoerpconnect_catalog.product import ProductProductExportMapper
from openerp.addons.magentoerpconnect.unit.backend_adapter import GenericAdapter


@magento(replacing=ProductProductExportMapper)
class ProductPriceExportMapper(ProductProductExportMapper):
    _model_name = 'magento.product.product'

    @mapping
    def price(self, record):
        price = record.lst_price
        return {'price': price}


@magento(replacing=product.ProductConfigurableExport)
class ProductConfigurablePriceExport(product.ProductConfigurableExport):
    _model_name = ['magento.product.product']

    def _after_export(self):
        """ Run the after export"""
        sess = self.session
        attribute_option_obj = sess.pool['magento.attribute.option']
        super_attribute_adapter = self.get_connector_unit_for_model(
            GenericAdapter, 'magento.super.attribute')
        vals = super_attribute_adapter.list(self.binding_record.magento_id)
        for vals_index in range(len(vals)):
            data = []
            magento_super_attr_id = vals[vals_index]['product_super_attribute_id']
            for index in range(len(vals[vals_index]['values'])):
                magento_value_index = vals[vals_index]['values'][index]['value_index']
                magento_attribute_option_ids = attribute_option_obj.search(
                    sess.cr, sess.uid,
                    [['magento_id', '=', magento_value_index]],
                    context=sess.context)
                attribute_option = attribute_option_obj.browse(
                    sess.cr, sess.uid,
                    magento_attribute_option_ids[0],
                    context=sess.context).openerp_id
                attribute_option_price = attribute_option.price
                data.append({
                    'value_index': magento_value_index,
                    'is_percent':'0',
                    'pricing_value': attribute_option_price
                })
            super_attribute_adapter.update(magento_super_attr_id, data)


@magento(replacing=product.ProductSuperAttributAdapter)
class ProductSuperAttributPriceAdapter(product.ProductSuperAttributAdapter):
    _model_name = ['magento.super.attribute']
    _magento_model = 'ol_catalog_product_link'

    def update(self, magento_super_attribute_id, data):
        """ Update Configurables Attributes """
        return self._call('%s.updateSuperAttributeValues'% self._magento_model,
                         [int(magento_super_attribute_id), data])
