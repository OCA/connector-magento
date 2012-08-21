# -*- encoding: utf-8 -*-
###############################################################################
#                                                                             #
#   magentoerpconnect_report_synchronizer for OpenERP                         #
#   Copyright (C) 2012 Akretion Sébastien BEAU <sebastien.beau@akretion.com>  #
#                                                                             #
#   This program is free software: you can redistribute it and/or modify      #
#   it under the terms of the GNU Affero General Public License as            #
#   published by the Free Software Foundation, either version 3 of the        #
#   License, or (at your option) any later version.                           #
#                                                                             #
#   This program is distributed in the hope that it will be useful,           #
#   but WITHOUT ANY WARRANTY; without even the implied warranty of            #
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the             #
#   GNU Affero General Public License for more details.                       #
#                                                                             #
#   You should have received a copy of the GNU Affero General Public License  #
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.     #
#                                                                             #
###############################################################################

from openerp.osv.orm import Model
from openerp.osv import fields

class account_invoice(Model):
    _inherit = "account.invoice"

    def ext_create(self, cr, uid, external_session, resources, mapping=None, mapping_id=None, context=None):
        ext_create_ids={}
        for resource_id, resource in resources.items():
            resource = resource[resource.keys()[0]]
            if resource['type'] == 'out_refund':
                method = "synoopenerpadapter_creditmemo.addInfo"
            elif resource['type'] == 'out_invoice':
                method = "synoopenerpadapter_invoice.addInfo"
            resource['reference'] = context.get('report_name')
            ext_create_ids[resource_id] = external_session.connection.call(method,
                        [
                            resource['customer_id'],
                            resource['order_increment_id'],
                            resource['reference'],
                            resource['amount'],
                            resource['date'],
                            resource['customer_name'],
                        ])
            super(account_invoice, self).ext_create(cr, uid, external_session, resources,
                                                    mapping=mapping, mapping_id=mapping_id, context=context)
        return ext_create_ids
