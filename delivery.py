# -*- encoding: utf-8 -*-
#########################################################################
#                                                                       #
#########################################################################
#                                                                       #
# Copyright (C) 2010 BEAU Sébastien                                     #
#                                                                       #
#This program is free software: you can redistribute it and/or modify   #
#it under the terms of the GNU General Public License as published by   #
#the Free Software Foundation, either version 3 of the License, or      #
#(at your option) any later version.                                    #
#                                                                       #
#This program is distributed in the hope that it will be useful,        #
#but WITHOUT ANY WARRANTY; without even the implied warranty of         #
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the          #
#GNU General Public License for more details.                           #
#                                                                       #
#You should have received a copy of the GNU General Public License      #
#along with this program.  If not, see <http://www.gnu.org/licenses/>.  #
#########################################################################

from osv import fields,osv
from tools.translate import _

class delivery_carrier(osv.osv):
    _inherit = "delivery.carrier"

    _columns = {
        'magento_code': fields.char('Magento Carrier Code', size=64, required=False),
        'magento_tracking_title': fields.char('Magento Tracking Title', size=64, required=False),
    }
    
    def check_ext_carrier_reference(self, cr, uid, id, magento_incrementid, context):
        conn = context and context.get('conn_obj', False) or False
        mag_carrier = conn.call('sales_order_shipment.getCarriers', [magento_incrementid])
        carrier = self.read(cr, uid, id, ['magento_code', 'name'], context=context)
        if not carrier['magento_code'] in mag_carrier.keys():
            raise osv.except_osv(_("Error"), _("The carrier %s don't have a magento_code valid!! Indeed the value %s is not in the magento carrier list %s" %(carrier['name'], carrier['magento_code'], mag_carrier.keys())))
        return True
delivery_carrier()

