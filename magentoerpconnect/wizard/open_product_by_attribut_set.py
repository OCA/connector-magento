# -*- encoding: utf-8 -*-
#################################################################################
#                                                                               #
#    Magentoerpconnect for OpenERP                                              #
#    Copyright (C) 2011 Akretion Sébastien BEAU <sebastien.beau@akretion.com>   #
#                                                                               #
#    This program is free software: you can redistribute it and/or modify       #
#    it under the terms of the GNU Affero General Public License as             #
#    published by the Free Software Foundation, either version 3 of the         #
#    License, or (at your option) any later version.                            #
#                                                                               #
#    This program is distributed in the hope that it will be useful,            #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of             #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the              #
#    GNU Affero General Public License for more details.                        #
#                                                                               #
#    You should have received a copy of the GNU Affero General Public License   #
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.      #
#                                                                               #
#################################################################################

from openerp.osv.orm import TransientModel
from openerp.osv import fields


class open_product_by_attribut_set(TransientModel):
    _name = 'open.product.by.attribut.set'
    _description = 'Wizard to open product by attributs set'
    _columns = {
        'attributs_set':fields.many2one('magerp.product_attribute_set', 'Attributs Set'),
        }

    def open_product_by_attribut(self, cr, uid, ids, context=None):
        """
        Opens Product by Attributs
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of account chart’s IDs
        @return: dictionary of Product list window for a given attributs set
        """
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        if context is None:
            context = {}
        attribute_set = self.browse(cr, uid, ids[0], context=context).attributs_set
        data = self.read(cr, uid, ids, [], context=context)[0]
        result = mod_obj.get_object_reference(cr, uid, 'product', 'product_normal_action')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        result['context'] = "{'set': %s}"% attribute_set.id
        result['domain'] = "[('set', '=', %s)]" % attribute_set.id
        result['name'] = attribute_set.attribute_set_name
        return result
