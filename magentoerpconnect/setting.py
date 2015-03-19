# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2013 Camptocamp SA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, fields


class MagentoConfigSettings(models.TransientModel):
    _inherit = 'connector.config.settings'

    module_magentoerpconnect_pricing = fields.Boolean(
        string="Prices are managed in OpenERP with pricelists",
        help="Prices are set in OpenERP and exported to Magento.\n\n"
             "This installs the module magentoerpconnect_pricing.",
    )
    module_magentoerpconnect_export_partner = fields.Boolean(
        string="Export Partners to Magento (experimental)",
        help="This installs the module magentoerpconnect_export_partner.",
    )
