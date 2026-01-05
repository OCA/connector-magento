# -*- coding: utf-8 -*-
# Copyright (c) 2015 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openerp.addons.magentoerpconnect import sale
from openerp.addons.connector.unit.mapper import mapping
from openerp.addons.magentoerpconnect.backend import magento


@magento(replacing=sale.SaleOrderPaymentImportMapper)
class SaleOrderImportMapper(sale.SaleOrderPaymentImportMapper):

    @mapping
    def payment(self, record):
        vals = super(SaleOrderImportMapper, self).payment(record)
        payment_method_id = vals.get('payment_method_id')
        if not payment_method_id:
            return vals
        payment_method = self.env['payment.method'].browse(payment_method_id)
        if payment_method.transaction_id_path:
            value = record
            for key in payment_method.transaction_id_path.split('.'):
                value = value.get(key)
                if not value:
                    break
            vals['transaction_id'] = value
        return vals
