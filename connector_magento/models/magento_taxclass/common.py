# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import xmlrpc.client
from odoo import models, fields
from odoo.addons.connector.exception import IDMissingInBackend
from odoo.addons.component.core import Component
from ...components.backend_adapter import MAGENTO_DATETIME_FORMAT

_logger = logging.getLogger(__name__)


class MagentoTaxClass(models.Model):
    _name = 'magento.account.tax'
    _inherit = 'magento.binding'
    _inherits = {'account.tax': 'odoo_id'}
    _description = 'Magento Tax Class'

    odoo_id = fields.Many2one(comodel_name='account.tax',
                              string='Tax',
                              required=True,
                              ondelete='restrict')
    class_name = fields.Char('Magento Class Name')
    class_type = fields.Selection([
        ('PRODUCT', 'Product'),
        ('CUSTOMER', 'Customer'),
        ('Shipping', 'Shipping'),
    ])


class AccountTax(models.Model):
    _inherit = 'account.tax'

    magento_bind_ids = fields.One2many(
        comodel_name='magento.account.tax',
        inverse_name='odoo_id',
        string="Magento Bindings",
    )


class AccountTaxAdapter(Component):
    _name = 'magento.account.tax.adapter'
    _inherit = 'magento.adapter'
    _apply_on = 'magento.account.tax'

    _magento_model = 'taxClasses'
    _magento2_model = 'taxClasses'
    _magento2_key = 'class_id'
    _magento2_search = 'taxClasses/search'
    _admin_path = '/{model}/index/'
