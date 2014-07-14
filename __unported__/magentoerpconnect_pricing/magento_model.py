# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2013 Camptocamp SA
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
from openerp.tools.translate import _
from openerp.addons.connector.session import ConnectorSession
from .product import export_product_price


class magento_backend(orm.Model):
    _inherit = 'magento.backend'

    def _get_pricelist_id(self, cr, uid, context=None):
        data_obj = self.pool.get('ir.model.data')
        ref = data_obj.get_object_reference(cr, uid, 'product', 'list0')
        if ref:
            return ref[1]
        return False

    _columns = {
        'pricelist_id': fields.many2one('product.pricelist',
                                        'Pricelist',
                                        required=True,
                                        domain="[('type', '=', 'sale')]",
                                        help='The price list used to define '
                                             'the prices of the products in '
                                             'Magento.'),
    }

    _defaults = {
        'pricelist_id': _get_pricelist_id,
    }

    def onchange_pricelist_id(self, cr, uid, ids, pricelist_id, context=None):
        if not ids:  # new record
            return {}
        warning = {
            'title': _('Warning'),
            'message': _('If you change the pricelist of the backend, '
                         'the price of all the products will be updated '
                         'in Magento.')
        }
        return {'warning': warning}

    def _update_default_prices(self, cr, uid, ids, context=None):
        """ Update the default prices of the products linked with
        this backend.

        The default prices are linked with the 'Admin' website (id: 0).
        """
        website_obj = self.pool.get('magento.website')
        website_ids = website_obj.search(cr, uid,
                                         [('backend_id', 'in', ids),
                                          ('magento_id', '=', '0')],
                                         context=context)
        website_obj.update_all_prices(cr, uid, website_ids, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        if 'pricelist_id' in vals:
            self._update_default_prices(cr, uid, ids, context=context)
        return super(magento_backend, self).write(cr, uid, ids, vals, context=context)


class magento_website(orm.Model):
    _inherit = 'magento.website'

    _columns = {
        'pricelist_id': fields.many2one('product.pricelist',
                                        'Pricelist',
                                        domain="[('type', '=', 'sale')]",
                                        help='The pricelist used to define '
                                             'the prices of the products in '
                                             'Magento for this website.\n'
                                             'Choose a pricelist only if the '
                                             'prices are different for this '
                                             'website.\n'
                                             'When empty, the default price '
                                             'will be used.'),
    }

    def update_all_prices(self, cr, uid, ids, context=None):
        """ Update the prices of all the products linked to the
        website. """
        if not hasattr(ids, '__iter__'):
            ids = [ids]
        for website in self.browse(cr, uid, ids, context=context):
            session = ConnectorSession(cr, uid, context=context)
            if website.magento_id == '0':
                # 'Admin' website -> default values
                # Update the default prices on all the products.
                binding_ids = website.backend_id.product_binding_ids
            else:
                binding_ids = website.product_binding_ids
            for binding in binding_ids:
                export_product_price.delay(session,
                                           'magento.product.product',
                                           binding.id,
                                           website_id=website.id)
        return True

    def onchange_pricelist_id(self, cr, uid, ids, pricelist_id, context=None):
        if not ids:  # new record
            return {}
        warning = {
            'title': _('Warning'),
            'message': _('If you change the pricelist of the website, '
                         'the price of all the products linked with this '
                         'website will be updated in Magento.')
        }
        return {'warning': warning}

    def write(self, cr, uid, ids, vals, context=None):
        if 'pricelist_id' in vals:
            self.update_all_prices(cr, uid, ids, context=context)
        return super(magento_website, self).write(cr, uid, ids, vals, context=context)
