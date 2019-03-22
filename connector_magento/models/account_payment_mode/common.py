# -*- coding: utf-8 -*-
# © 2013-2017 Guewen Baconnier,Camptocamp SA,Akretion
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields
from odoo.addons.component.core import Component


class MagentoAccountPaymentMode(models.Model):
    _name = 'magento.account.payment.mode'
    _inherit = 'magento.binding'
    _inherits = {'account.payment.mode': 'odoo_id'}
    _description = 'Magento Payment Mode'

    odoo_id = fields.Many2one(comodel_name='account.payment.mode',
                              string='Odoo Payment Mode',
                              required=True,
                              ondelete='restrict')
    magento_payment_method = fields.Char('Magento Payment Method Code')


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
    magento_bind_ids = fields.One2many(
        comodel_name='magento.account.payment.mode',
        inverse_name='odoo_id',
        string="Magento Bindings",
    )


class MagentoProductVariantModelBinder(Component):
    """ Bind records and give odoo/magento ids correspondence

    Binding models are models called ``magento.{normal_model}``,
    like ``magento.res.partner`` or ``magento.product.product``.
    They are ``_inherits`` of the normal models and contains
    the Magento ID, the ID of the Magento Backend and the additional
    fields belonging to the Magento instance.
    """
    _name = 'magento.account.payment.mode.binder'
    _inherit = 'magento.binder'
    _apply_on = ['magento.account.payment.mode']
    _external_field = 'magento_payment_method'
