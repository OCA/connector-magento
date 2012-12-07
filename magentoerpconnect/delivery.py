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

from openerp.osv.orm import Model
from openerp.osv import fields
from openerp.osv.osv import except_osv
from openerp.tools.translate import _

class delivery_carrier(Model):
    _inherit = "delivery.carrier"

    def _carrier_code(self, cr, uid, ids, name, args, context=None):
        res = {}
        for carrier in self.browse(cr, uid, ids, context=context):
            if not carrier.magento_code:
                res[carrier.id] = False
                continue
            res[carrier.id] = carrier.magento_code.split('_')[0]
        return res

    _columns = {
        'magento_code': fields.char('Magento Carrier Code', size=64, required=False),
        'magento_tracking_title': fields.char('Magento Tracking Title', size=64, required=False),
        # in Magento, the delivery method is something like that:
        # tntmodule2_tnt_basic
        # where the first part before the _ is always the carrier code
        # in this example, the carrier code is tntmodule2
        'magento_carrier_code':
            fields.function(_carrier_code,
                            string='Magento Base Carrier Code',
                            size=32,
                            type='char')
    }

    def check_ext_carrier_reference(self, cr, uid, id,
                                    magento_incrementid, context=None):
        if context is None: context = {}
        conn = context.get('conn_obj', False)
        mag_carrier = conn.call(
            'sales_order_shipment.getCarriers', [magento_incrementid])
        carrier = self.read(
            cr, uid, id, ['magento_carrier_code', 'name'], context=context)
        if not carrier['magento_carrier_code'] in mag_carrier.keys():
            raise except_osv(
                _("Error"),
                _("The carrier %s doesn't have a magento_code valid !"
                  "The value %s is not in the carrier list %s "
                  "allowed by Magento") %
                (carrier['name'],
                 carrier['magento_carrier_code'],
                 mag_carrier.keys()))
        return True
delivery_carrier()

