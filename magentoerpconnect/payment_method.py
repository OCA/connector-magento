# -*- coding: utf-8 -*-
from openerp import models, fields


class PaymentMethod(models.Model):
    _inherit = "payment.method"

    create_invoice_on = fields.Selection(
        selection=[('open', 'Validate'),
                   ('paid', 'Paid')],
        string='Create invoice on action',
        help="Should the invoice be created in Magento "
             "when it is validated or when it is paid in OpenERP?\n"
             "If nothing is set, the option falls back to the same option "
             "on the Magento store related to the sales order.",
    )
