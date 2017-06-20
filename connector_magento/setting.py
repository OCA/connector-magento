# -*- coding: utf-8 -*-
# © 2013 Guewen Baconnier,Camptocamp SA,Akretion
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import models, fields


class MagentoConfigSettings(models.TransientModel):
    _inherit = 'connector.config.settings'

    module_connector_magento_pricing = fields.Boolean(
        string="Prices are managed in OpenERP with pricelists",
        help="Prices are set in OpenERP and exported to Magento.\n\n"
             "This installs the module connector_magento_pricing.",
    )
    module_connector_magento_export_partner = fields.Boolean(
        string="Export Partners to Magento (experimental)",
        help="This installs the module connector_magento_export_partner.",
    )
