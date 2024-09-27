# -*- coding: utf-8 -*-
# Copyright 2017 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)
from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping


class SaleOrderImportMapper(Component):
    _inherit = 'magento.sale.order.mapper'

    @mapping
    def payment(self, record):
        vals = super(SaleOrderImportMapper, self).payment(record)
        payment_mode_id = vals.get('payment_mode_id')
        if payment_mode_id:
            payment_mode = self.env['account.payment.mode'].browse(
                payment_mode_id)
            if payment_mode.transaction_id_path:
                value = record
                for key in payment_mode.transaction_id_path.split('.'):
                    value = value.get(key)
                    if not value:
                        break
                vals['transaction_id'] = value
        return vals
