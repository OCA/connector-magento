# -*- coding: utf-8 -*-
# Copyright (c) 2015 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields


class AccountPaymentMode(models.Model):
    _inherit = 'account.payment.mode'

    transaction_id_path = fields.Char(
        help=('Path to the value into the informations provided by Magento '
              'for a sale order. Values are provided as a json dict. If the '
              'transaction_id is in a sub dict the path must be specified '
              'by using dots between keys to the value.'))
