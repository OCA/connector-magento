# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier, David Beal, Chafique Delli
#    Copyright 2013 Camptocamp SA
#    Copyright 2013-14 Akretion
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

from openerp.osv import orm, fields
from openerp.addons.magentoerpconnect import product
from openerp.addons.magentoerpconnect.backend import magento
from openerp.addons.connector.unit.mapper import mapping


class magento_product_product(orm.Model):
    _inherit = 'magento.product.product'

    _columns = {
        'price_type': fields.selection([('dynamic', 'Dynamic'),('fixed', 'Fixed')],
            'Price Type'),
    }

    def product_type_get(self, cr, uid, context=None):
        option = ('bundle', 'Bundle Product')
        type_selection = super(magento_product_product, self).product_type_get(
            cr, uid, context=context)
        if option not in type_selection:
            type_selection.append(option)
        return type_selection

@magento(replacing=product.BundleProductImportMapper)
class BundleProductImportMapper(product.BundleProductImportMapper):
    _model_name = 'magento.product.product'

    @mapping
    def type(self, record):
        return {'type': 'service'}

    @mapping
    def price_type(self, record):
        if record['price_type'] == '0':
            price_type = 'dynamic'
        else:
            price_type = 'fixed'
        return {'price_type': price_type}
