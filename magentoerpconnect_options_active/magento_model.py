# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Markus Schneider
#    Copyright 2014 initOS GmbH & Co. KG
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

from openerp.osv import fields, orm


class magento_backend(orm.Model):

    _name = 'magento.backend'
    _inherit = 'magento.backend'

    def _select_product_active(self, cr, uid, context=None):
        return [('nothing', 'do nothing in OpenERP'),
                ('disable', 'disable in OpenERP'),
                ('no_sale', 'disable sale option'),
                ('no_sale_no_purchase', 'disable sale & purchase option')]

    _columns = {
        'product_active': fields.selection(
            _select_product_active,
            string='Handle disable products',
            required=True),
    }

    _defaults = {
        'product_active': 'disable',
    }
