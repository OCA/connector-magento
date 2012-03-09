# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2011-2012 Camptocamp SA
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

from osv import osv, fields


class Product(osv.osv):
    """Inherit product to use the default code as the Magento SKU. Copy the default code into the magento_sku field."""
    _inherit = 'product.product'

    _columns = {'magento_sku':fields.char('Magento SKU', size=64, readonly=True),}

    _sql_constraints = [('code_uniq', 'unique(default_code)', 'The code must be unique')]

    def _get_sku(self, cr, uid, vals, product=None, context=None):
        """
        Returns the SKU value.
        @param vals: vals to be created / modified
        @param product: optional browse instance of the product (when writing)
        """
        return vals['default_code']

    def create(self, cr, uid, vals, context=None):
        if vals.get('default_code'):
            vals['magento_sku'] = self._get_sku(cr, uid, vals, context=context)
        return super(Product, self).create(cr, uid, vals, context)

    def write(self, cr, uid, ids, vals, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        ids_to_write = ids[:]
        if vals.get('default_code'):
            for product in self.browse(cr, uid, ids, context=context):
                # write separately on each product if they are not already exported
                if not product.magento_exported:
                    new_vals = vals.copy()
                    new_vals['magento_sku'] = self._get_sku(cr, uid, new_vals, product=product, context=context)
                    super(Product, self).write(cr, uid, [product.id], new_vals, context=context)
                    ids_to_write.remove(product.id)

        return super(Product, self).write(cr, uid, ids_to_write, vals, context=context)

    def copy(self, cr, uid, id, default=None, context=None):
        if not default is None: default = {}
        default['default_code'] = False
        return super(Product, self).copy(cr, uid, id, default=default, context=context)

Product()
