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
from openerp.osv import orm, osv
#from openerp.tools.translate import _



@magento(replacing=sale.SaleOrderLineBundleImportMapper)
class SaleOrderLineBundleImportMapper(sale.SaleOrderLineBundleImportMapper):
    _model_name = 'magento.sale.order.line'

    def price_is_zero(self, record):
        sess = self.session
        mag_product_model = sess.pool['magento.product.product']
        mag_product_ids = mag_product_model.search(
            sess.cr, sess.uid,
            [('magento_id', '=', record['product_id'])])
        for mag_product_id in mag_product_ids:
            mag_product = mag_product_model.browse(
                sess.cr, sess.uid, mag_product_id)
            if record['product_type'] == 'bundle' \
                    and mag_product.price_type == 'dynamic':
                return True


@magento(replacing=sale.SaleOrderImport)
class SaleOrderBundleImport(sale.SaleOrderImport):
    _model_name = ['magento.sale.order']

    def _link_hierarchical_lines(self, binding_id):
        session = self.session
        order_line_ids = session.search(
            'magento.sale.order.line',
            [('magento_order_id', '=', binding_id)])
        bundle_ids = {}
        mag_id_2_openerp_id = {}
        for line in session.browse('magento.sale.order.line', order_line_ids):
            if line.magento_parent_item_id:
                bundle_ids.setdefault(
                    line.magento_parent_item_id, []).append(line.id)
            mag_id_2_openerp_id[line.magento_id] = line.openerp_id.id
        for mag_parent_item_id, mag_child_line_ids in bundle_ids.iteritems():
            parent_line_id = mag_id_2_openerp_id[str(mag_parent_item_id)]
            session.write('magento.sale.order.line', mag_child_line_ids, {
                'line_parent_id': parent_line_id,
                })


#class sale_order(orm.Model):
#    _inherit = 'sale.order'
#
#    def copy(self, cr, uid, id, default=None, context=None):
#        if default is None:
#            default = {}
#        default = {'order_line': False}
#        res = super(sale_order, self).copy(cr, uid, id,
#                                                 default=default,
#                                                 context=context)
#        #for origin_order_line in self.browse(cr, uid, id, context=context).order_line:
#            # copier ligne par ligne de origin_order vers copy_order
#
#        #copy_lines = self.browse(cr, uid, res, context=context).order_line
#        #origin_line_ids = sorted(r.id for r in self.browse(
#        #    cr, uid, id, context=context).order_line)
#        #copy_line_ids = sorted(r.id for r in copy_lines)
#        ## build mapping
#        #line_map = dict(zip(origin_line_ids, copy_line_ids))
#        #sale_line_obj = self.pool.get('sale.order.line')
#        #for copy_line in copy_lines:
#        #    if copy_line.line_parent_id:
#        #        if copy_line.line_parent_id.id not in line_map:
#        #            raise osv.except_osv(_('Error!'),
#        #                                 _('No bundle parent line was found.'))
#        #        copy_parent_id = line_map[copy_line.line_parent_id.id]
#        #        sale_line_obj.write(
#        #            cr, uid, copy_line.id, {'line_parent_id': copy_parent_id})
#
#        return res