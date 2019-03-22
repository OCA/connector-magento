# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import xmlrpclib
from odoo import models, fields
from odoo.addons.connector.exception import IDMissingInBackend
from odoo.addons.component.core import Component
from ...components.backend_adapter import MAGENTO_DATETIME_FORMAT

_logger = logging.getLogger(__name__)

'''
    "payment": {
        "account_status": null,
        "additional_information": [
            "249.99",
            "EUR",
            "PAYPAL",
            "PayPal",
            "de",
            "10245719",
            "SUCCESS",
            "7V2b6R0f9d",
            "300008000000365",
            "1193",
            "before",
            "",
            "e542f0fa6d206b2277256eb47655c54c0dccddc39d7c5136acd60bab3186e447707b3d27686275e08dbb0e188892c5fe32fb8ee932a94cb6ffdf003efb1538e6",
            "RNB9K5RQU5N9L",
            "Daniel_Haine@web.de",
            "Haine",
            "Daniel",
            "Daniel Haine",
            "Deutschland",
            "DE",
            "Neustadt",
            "SAS",
            "Folgenweg 29",
            "",
            "01844"
        ],
        "amount_ordered": 249.99,
        "amount_paid": 249.99,
        "base_amount_ordered": 249.99,
        "base_amount_paid": 249.99,
        "base_amount_paid_online": 249.99,
        "base_shipping_amount": 0,
        "base_shipping_captured": 0,
        "cc_exp_year": "0",
        "cc_last4": null,
        "cc_ss_start_month": "0",
        "cc_ss_start_year": "0",
        "entity_id": 392,
        "last_trans_id": "tmp_5c6f405e9414f",
        "method": "wirecard_checkoutpage_paypal",
        "parent_id": 392,
        "shipping_amount": 0,
        "shipping_captured": 0
    },
'''
class MagentoAccountPayment(models.Model):
    _name = 'magento.account.payment'
    _inherit = 'magento.binding'
    _inherits = {'account.payment': 'odoo_id'}
    _description = 'Magento Payment'

    odoo_id = fields.Many2one(comodel_name='account.payment',
                              string='Odoo Payment',
                              required=True,
                              ondelete='restrict')
    order_id = fields.Many2one(comodel_name='sale.order',
                              string='Sale Order',
                              required=True,
                              ondelete='restrict')
    additional_information = fields.Text('Payment Provider Information')
    account_status = fields.Char('Account Status')
    amount_ordered = fields.Float('Amount Ordered', default=0.0)
    amount_paid = fields.Float('Amount Paid', default=0.0)
    last_trans_id = fields.Char('Transaktion ID')


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    magento_bind_ids = fields.One2many(
        comodel_name='magento.account.payment',
        inverse_name='odoo_id',
        string="Magento Bindings",
    )


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    magento_payment_ids = fields.One2many(
        comodel_name='magento.account.payment',
        inverse_name='order_id',
        string="Magento Payments",
    )
