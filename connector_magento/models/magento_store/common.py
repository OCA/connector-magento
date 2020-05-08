# Copyright 2013-2019 Camptocamp SA
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import models, fields
from odoo.addons.component.core import Component


class MagentoStore(models.Model):
    _name = 'magento.store'
    _inherit = ['magento.binding', 'magento.config.specializer']
    _description = 'Magento Store'
    _parent_name = 'website_id'

    name = fields.Char()
    website_id = fields.Many2one(
        comodel_name='magento.website',
        string='Magento Website',
        required=True,
        readonly=True,
        ondelete='cascade',
    )
    backend_id = fields.Many2one(
        comodel_name='magento.backend',
        related='website_id.backend_id',
        string='Magento Backend',
        store=True,
        readonly=True,
        # override 'magento.binding', can't be INSERTed if True:
        required=False,
    )
    storeview_ids = fields.One2many(
        comodel_name='magento.storeview',
        inverse_name='store_id',
        string="Storeviews",
        readonly=True,
    )
    send_picking_done_mail = fields.Boolean(
        string='Send email notification on picking done',
        help="Does the picking export/creation should send "
             "an email notification on Magento side?",
    )
    send_invoice_paid_mail = fields.Boolean(
        string='Send email notification on invoice validated/paid',
        help="Does the invoice export/creation should send "
             "an email notification on Magento side?",
    )
    create_invoice_on = fields.Selection(
        selection=[('open', 'Validate'),
                   ('paid', 'Paid')],
        string='Create invoice on action',
        default='paid',
        required=True,
        help="Should the invoice be created in Magento "
             "when it is validated or when it is paid in Odoo?\n"
             "This only takes effect if the sales order's related "
             "payment method is not giving an option for this by "
             "itself. (See Payment Methods)",
    )
    is_multi_company = fields.Boolean(related="backend_id.is_multi_company")


class StoreAdapter(Component):
    _name = 'magento.store.adapter'
    _inherit = 'magento.adapter'
    _apply_on = 'magento.store'

    _magento_model = 'ol_groups'
    _magento2_model = 'store/storeGroups'
    _admin_path = 'system_store/editGroup/group_id/{id}'
