# -*- coding: utf-8 -*-
from openerp.osv import orm, fields


class payment_invoice(orm.Model):
    _inherit = "payment.method"

    _columns = {
        'create_invoice_on': fields.selection(
            [('open', 'Validate'),
             ('paid', 'Paid')],
            'Create invoice on action',
            help="Should the invoice be created in Magento "
                 "when it is validated or when it is paid in OpenERP?\n"
                 "If nothing is set, the option falls back to the same option "
                 "on the Magento store related to the sales order."),
    }
