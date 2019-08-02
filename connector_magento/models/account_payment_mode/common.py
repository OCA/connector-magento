# © 2013-2019 Guewen Baconnier,Camptocamp SA,Akretion
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields


class AccountPaymentMode(models.Model):
    _inherit = "account.payment.mode"

    create_invoice_on = fields.Selection(
        selection=[('open', 'Validate'),
                   ('paid', 'Paid')],
        string='Create invoice on action',
        help="Should the invoice be created in Magento "
             "when it is validated or when it is paid in Odoo?\n"
             "If nothing is set, the option falls back to the same option "
             "on the Magento store related to the sales order.",
    )
