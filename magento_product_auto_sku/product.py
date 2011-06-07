# -*- encoding: utf-8 -*-
##############################################################################
#
#    Author Guewen Baconnier. Copyright Camptocamp SA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import osv, fields

class Product(osv.osv):
    " Inherit product to add the sequence on the Magento SKU field"
    _inherit = 'product.product'

    _columns = {
                'magento_sku':fields.char('Magento SKU', size=64, readonly=True),
                }

    _defaults = {
                 'magento_sku':lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'product.magento.sku'),
                }

    def copy(self, cr, uid, id, default=None, context=None):
        if context is None:
            context = {}
        if default is None:
            default = {}

        default['magento_sku'] = self.pool.get('ir.sequence').get(cr, uid, 'product.magento.sku')

        return super(Product, self).copy(cr, uid, id, default=default, context=context)

Product()
