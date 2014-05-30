# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Chafique Delli
#    Copyright 2014 Akretion SA
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

from openerp.addons.magentoerpconnect import sale
from openerp.addons.magentoerpconnect.backend import magento
from openerp.osv import fields, orm
from openerp.addons.connector.unit.mapper import mapping



@magento(replacing=sale.SaleOrderLineImportMapper)
class SaleOrderLineBundleImportMapper(sale.SaleOrderLineImportMapper):
    _model_name = 'magento.sale.order.line'

    direct = sale.SaleOrderLineImportMapper.direct + [
        ('parent_item_id', 'magento_parent_item_id'),
        ]

    @mapping
    def price(self, record):
        sess = self.session
        mag_product_model = sess.pool['magento.product.product']
        mag_product_ids = mag_product_model.search(
            sess.cr, sess.uid,
            [('magento_id', '=', record['product_id'])])
        mag_product = mag_product_model.browse(sess.cr,
                                               sess.uid,
                                               mag_product_ids[0])
        result = {}
        if record['product_type'] == 'bundle' and mag_product.price_type == 'dynamic':
            result['price_unit'] = 0.0
        else:
            #order_line_mapper = self.environment.get_connector_unit(sale.SaleOrderLineImportMapper)
            result = super(SaleOrderLineBundleImportMapper, self).price(record)
            #result = order_line_mapper.price(record)

            #base_row_total = float(record['base_row_total'] or 0.)
            #base_row_total_incl_tax = float(record['base_row_total_incl_tax'] or 0.)
            #qty_ordered = float(record['qty_ordered'])
            #if self.backend_record.catalog_price_tax_included:
            #    result['price_unit'] = base_row_total_incl_tax / qty_ordered
            #else:
            #    result['price_unit'] = base_row_total / qty_ordered
        return result


@magento(replacing=sale.SaleOrderImport)
class SaleOrderBundleImport(sale.SaleOrderImport):
    _model_name = ['magento.sale.order']


    def _merge_sub_items(self, product_type, top_item, child_items):
        """
        In the module magentoerpconnect_bundle_split, instead of merging
        the child items, we create a sale order line for each of them.
        As the bundle item price is the same
        as the sum of all the items, we set its price at 0.0

        :param top_item: main item (bundle, configurable)
        :param child_items: list of childs of the top item
        :return: list of items
        """
        if product_type == 'bundle':
            items = []
            bundle_item = top_item.copy()
            items = [child for child in child_items]
            items.insert(0, bundle_item)
            return items
        #order_import = self.environment.get_connector_unit(sale.SaleOrderImport)
        return super(SaleOrderBundleImport, self)._merge_sub_items(
            product_type, top_item, child_items)
        #return order_import._merge_sub_items(product_type, top_item, child_items)

    def _create(self, data):
        session = self.session
        #order_import = self.environment.get_connector_unit(sale.SaleOrderImport)
        order_id = super(SaleOrderBundleImport, self)._create(data)
        #order_id = order_import._create(data)
        order_line_ids = session.search(
            'magento.sale.order.line',
            [('magento_order_id', '=', order_id)])
        bundle_ids = {}
        mag_id_2_openerp_id = {}
        for line in session.browse('magento.sale.order.line', order_line_ids):
            if line.magento_parent_item_id:
                bundle_ids.setdefault(line.magento_parent_item_id, []).append(line.id)
            mag_id_2_openerp_id[line.magento_id] = line.openerp_id.id
        for mag_parent_item_id, mag_child_line_ids in bundle_ids.iteritems():
            parent_line_id = mag_id_2_openerp_id[str(mag_parent_item_id)]
            session.write('magento.sale.order.line', mag_child_line_ids, {
                'line_parent_id': parent_line_id,
                })
        return order_id


class magento_sale_order_line(orm.Model):
    _inherit = 'magento.sale.order.line'

    _columns = {
        'magento_parent_item_id': fields.integer('Magento Parent Item ID'),
        }
