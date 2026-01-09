# -*- coding: utf-8 -*-
# © 2016  Laetitia Gangloff, Acsone SA/NV (http://www.acsone.eu)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    magento_company_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Magento Company User",
        help="The user attached to the company use to import sale order",
        domain="[('company_id', '=', id)]"
    )
