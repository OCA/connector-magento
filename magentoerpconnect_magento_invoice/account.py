# -*- encoding: utf-8 -*-
###############################################################################
#
#   magentoerpconnect_magento_invoice for OpenERP
#   Copyright (C) 2012-TODAY Akretion <http://www.akretion.com>. All Rights Reserved
#   @author Sébastien BEAU <sebastien.beau@akretion.com>
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as
#   published by the Free Software Foundation, either version 3 of the
#   License, or (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################


from openerp.osv.orm import Model

class account_invoice(Model):
    _inherit = "account.invoice"

    def action_move_create(self, cr, uid, ids, context=None):
        if context is None:
            context = {'lang': 'en_US'}
        for invoice in self.browse(cr, uid, ids, context=context):
            ext_invoice_id = self._export_one_invoice(cr, uid, invoice, context=context)
            invoice.write({'internal_number': ext_invoice_id}, context=context)
        return super(account_invoice, self).action_move_create(cr, uid, ids, context=context)

