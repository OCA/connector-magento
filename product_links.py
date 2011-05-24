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

from osv import fields, osv
from tools.translate import _
from magentoerpconnect import magerp_osv
import netsvc


class product_link(magerp_osv.magerp_osv):
    _inherit = 'product.link'

    _columns = {
        'sequence': fields.integer('Position'),
#        'quantity': fields.integer('Quantity'), Magento documentation speaks about the "quantity" option but I could not find its usage. It seems that it is not used.
    }

    def ext_export(self, cr, uid, ids, external_referential_ids=[], defaults={}, context=None):
        if context is None:
            context = {}
        logger = netsvc.Logger()
        conn = context.get('conn_obj', False)
        for link in self.browse(cr, uid, ids, context):
            if not link.product_id.magento_sku or not link.linked_product_id.magento_sku:
                continue

            data = {
                'type': link.type,
                'product_sku': link.product_id.magento_sku,
                'linked_product_sku': link.linked_product_id.magento_sku,
                'values': {}
            }
            if link.sequence > 0:
                data['values']['position'] = link.sequence
            # Magento automatically modify the existing link when we assign it again, so we can call create at each modification
            self.ext_create(cr, uid, data, conn, 'catalog_product_link.assign', link.id, context)
            logger.notifyChannel('ext synchro', netsvc.LOG_INFO, _("Assigned product link of type %s from OpenERP product id %s to product id %s on Magento successfully") % (link.type, link.product_id.id, link.linked_product_id.id,))

    def ext_create(self, cr, uid, data, conn, method, oe_id, context):
        return super(magerp_osv.magerp_osv, self).ext_create(cr, uid,
                                                             [data['type'],
                                                              data['product_sku'],
                                                              data['linked_product_sku'],
                                                              data['values']],
                                                             conn,
                                                             method,
                                                             oe_id,
                                                             context)

    #TODO delete links on magento which doesn't exist on openerp
    # Move in product.product. Call on product export?
#    def ext_delete_links(self, cr, uid, ids, external_referential_id, context=None):
#        """ Delete product links on Magento which doesn't exist on OpenERP
#        """
#        if not context or not context.get('conn_obj',False):
#            raise Exception('No connection object in context')
#        conn = context['conn_obj']
#
#        for product in self.browse(cr, uid, ids, context):
#
#            if not product.magento_exportable or not product.magento_sku:
#                return
#
#            for type_selection in self.pool.get('product.link').get_link_type_selection(cr, uid, context):
#                type = type_selection[0]
#                mage_links = conn.call('product_link.list', [type, product.magento_sku])
#                for mage_link in mage_links:
#                    linked_product_id = self.extid_to_oeid(cr,
#                                                           uid,
#                                                           int(mage_link['product_id']),
#                                                           external_referential_id,
#                                                           context)
#                    oerp_link = self.search(cr, uid,
#                                            [('type', '=', type),
#                                             ('product_id', '=', product.id),
#                                             ('linked_product_id', '=', linked_product_id)])
#
#                    if not oerp_link: # delete the link from magento
#                        conn.call('product_link.remove', [type, product.magento_sku, mage_link['sku']])

product_link()

