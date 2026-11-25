# -*- coding: utf-8 -*-
# © 2016 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import models, fields


class AccountTax(models.Model):
    _inherit = 'account.tax'

    magento_tax_id = fields.Integer('Magento Tax ID')
