# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2014 initOS GmbH & Co. KG (<http://www.initos.com>).
#    Author Katja Matthes <katja.matthes at initos.com>
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
from openerp.addons.magentoerpconnect.sale import SaleOrderImport
from openerp.addons.magentoerpconnect.sale import SaleOrderLineImportMapper
from .backend import magento1700_bundle_import_childs
from openerp.osv import fields, orm, osv
from openerp.tools.translate import _

class sale_order_line(orm.Model):
    _inherit = 'sale.order.line'

    def _get_is_bundle_item(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for item in self.browse(cr, uid, ids, context=context):
            res[item.id] = (item.bundle_parent_id.id == False)
        return res

    def _set_is_bundle_item(self, cr, uid, id, field_name, field_value, arg, context):
        line = self.browse(cr, uid, id, context=context)
        order_lines = line.order_id.order_line
        last_parent = False
        # already parent will never updated
        if line.bundle_parent_id.id != False:
            return
        # bundles are never recursive
        if self.has_bundle_children(cr, uid, [id], context=context):
            return
        if not field_value:
            for ol in order_lines:
                if ol.id == line.id:
                    return self.write(cr, uid, [line.id], {'bundle_parent_id': last_parent})
                if ol.bundle_parent_id.id == False:
                    last_parent = ol.id

        return False

    def has_bundle_children(self, cr, uid, ids, context=None):
        "Returns True iff this order line has bundle children"
        # Don't use a one2many field because this breaks copying
        return self.search(cr, uid, [('bundle_parent_id', '=', ids[0])], count=True) > 0

    _columns = {
        'bundle_parent_id': fields.many2one('sale.order.line', 'Bundle Parent Line', domain="[('bundle_parent_id','=',False)]", ondelete='cascade', help="Link to bundle parent item.", select=True),
        'is_bundle_item': fields.function(
                    _get_is_bundle_item, method=True,
                    fnct_inv=_set_is_bundle_item,
                    string='No Bundle Child', type='boolean',
                    help="""True for Bundle Parent Items and Single Items (will appear on invoice), false for Bundle Child Items (will not appear on invoice)"""),
        }

    _defaults = {
        'is_bundle_item': True,
    }

    def _check_recursion(self, cr, uid, ids, context=None):
        level = 100
        while len(ids):
            cr.execute('select distinct bundle_parent_id from sale_order_line where id IN %s', (tuple(ids),))
            ids = filter(None, map(lambda x:x[0], cr.fetchall()))
            if not level:
                return False
            level -= 1
        return True

    _constraints = [
        (_check_recursion, 'Error ! You cannot create recursive parent.', ['bundle_parent_id'])
    ]

class magento_sale_order_line(orm.Model):
    _inherit = 'magento.sale.order.line'

    _columns = {
        'magento_parent_item_id': fields.integer('Magento ID of Parent Item'),
        }


class sale_order(orm.Model):
    _inherit = 'sale.order'

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        res = super(sale_order, self).copy(cr, uid, id,
                                                 default=default,
                                                 context=context)

        copy_lines = self.browse(cr, uid, res, context=context).order_line
        origin_line_ids = sorted(r.id for r in self.browse(cr, uid, id, context=context).order_line)
        copy_line_ids = sorted(r.id for r in copy_lines)
        # build mapping
        line_map = dict(zip(origin_line_ids, copy_line_ids))

        sale_line_obj = self.pool.get('sale.order.line')
        for copy_line in copy_lines:
            if copy_line.bundle_parent_id:
                if copy_line.bundle_parent_id.id not in line_map:
                    raise osv.except_osv(_('Error!'), _('No bundle parent line was found.'))
                copy_parent_id = line_map[copy_line.bundle_parent_id.id]
                sale_line_obj.write(cr, uid, copy_line.id, {'bundle_parent_id': copy_parent_id})

        return res

class magento_sale_order(orm.Model):
    _inherit = "magento.sale.order"

    def create(self, cr, uid, vals, context=None):
        order_id = super(magento_sale_order, self).create(cr, uid, vals, context=context)

        order_line_obj = self.pool.get('magento.sale.order.line')
        order = self.browse(cr, uid, order_id, context=context)

        bundle_ids = {}
        for line in order.magento_order_line_ids:
            if line.magento_parent_item_id:
                bundle_ids.setdefault(line.magento_parent_item_id, []).append(line.id)

        for parent_item_id, child_line_ids in bundle_ids.iteritems():
            parent_line_ids = order_line_obj.search(cr, uid,
                [('magento_id', '=', parent_item_id)])
            if not parent_line_ids:
                continue
            # get openerp id to link the parent order line
            parent_line_id = order_line_obj.browse(cr, uid, parent_line_ids[0], context=context).openerp_id.id
            order_line_obj.write(cr, uid, child_line_ids,
                    {'bundle_parent_id': parent_line_id},
                       context=context)

        return order_id

@magento1700_bundle_import_childs
class BundleSaleOrderImport(SaleOrderImport):
    _model_name = ['magento.sale.order']

    def _merge_sub_items(self, product_type, top_item, child_items):
        """Manage the sub items of the magento sale order lines. A top item contains one
        or many child_items. Here is the handling for bundle products.

        We keep booth parent products and children."""
        if product_type == 'bundle':
            items = [child for child in child_items]
            for child in items:
                if not child['row_total_incl_tax']:
                    child['row_total_incl_tax'] = 0
            bundle_item = top_item.copy()
            items.insert(0, bundle_item)
            return items
        else:
            return SaleOrderImport._merge_sub_items(self, product_type, top_item, child_items)

@magento1700_bundle_import_childs
class BundleSaleOrderLineImportMapper(SaleOrderLineImportMapper):

    direct = SaleOrderLineImportMapper.direct + [('parent_item_id', 'magento_parent_item_id')]
