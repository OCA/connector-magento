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
import os

class account_invoice(Model):
    _inherit = "account.invoice"

    def _export_one_resource(self, cr, uid, external_session, invoice_id, context=None):
        #TODO think about a better solution to pass the report_name
        context['report_name'] = self._send_invoice_report(cr, uid, external_session,
                                                             invoice_id, context=context)
        return super(account_invoice, self)._export_one_resource(cr, uid, external_session, 
                                                                    invoice_id, context=context)

    def _send_invoice_report(self, cr, uid, external_session, invoice_id, context=None):
        if context is None: context={}
        context['active_model'] = self._name
        invoice = self.browse(cr, uid, invoice_id, context=context)
        invoice_number = invoice.number.replace('/', '-')
        invoice_path = self._get_invoice_path(cr, uid, external_session, invoice, context=context)
        if not external_session.sync_from_object.invoice_report:
            raise except_osv(_("User Error"), _("You must define a report for the invoice for your sale shop"))
        report_name = "report.%s"%external_session.sync_from_object.invoice_report.report_name
        return self.send_report(cr, uid, external_session.file_session, [invoice.id], report_name, 
                                                    invoice_number, invoice_path, add_extension=True, context=context)

    def _get_invoice_path(self, cr, uid, external_session, invoice, context=None):
        ref_id = external_session.referential_id.id
        ext_partner_id = invoice.partner_id.get_extid(ref_id, context=context)
        ext_sale_id = invoice.sale_ids[0].get_extid(ref_id, context=context)
        if invoice.type == 'out_invoice':
            basepath = 'invoice'
        elif invoice.type == 'out_refund':
            basepath = 'creditmemo'
        return os.path.join(basepath, str(ext_partner_id), str(ext_sale_id))

    def ext_create_one_invoice(self, cr, uid, external_session, resource_id, resource, context=None):
        data = resource[resource.keys()[0]]
        if data['type'] == 'out_refund':
            method = "synoopenerpadapter_creditmemo.addInfo"
        elif data['type'] == 'out_invoice':
            method = "synoopenerpadapter_invoice.addInfo"
        filename, extension = context.get('report_name').rsplit('.', 1)
        if extension != 'pdf':
            raise except_osv(
                _("User Error"),
                _("The report selected for the invoice for your sale shop must be in the format pdf")
                )
        res = external_session.connection.call(method,
                    [
                        data['customer_id'],
                        data['order_increment_id'],
                        filename,
                        data['amount'],
                        data['date'],
                        data['customer_name'],
                    ])
        super(account_invoice, self).ext_create_one_invoice(cr, uid, external_session,
                                                    resource_id, resource, context=context)
        return res
