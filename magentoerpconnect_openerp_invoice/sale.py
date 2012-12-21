# -*- encoding: utf-8 -*-
###############################################################################
#                                                                             #
#   magentoerpconnect_openerp_invoice for OpenERP                             #
#   Copyright (C) 2012 Akretion Sébastien BEAU <sebastien.beau@akretion.com>  #
#                                                                             #
#   This program is free software: you can redistribute it and/or modify      #
#   it under the terms of the GNU Affero General Public License as            #
#   published by the Free Software Foundation, either version 3 of the        #
#   License, or (at your option) any later version.                           #
#                                                                             #
#   This program is distributed in the hope that it will be useful,           #
#   but WITHOUT ANY WARRANTY; without even the implied warranty of            #
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the             #
#   GNU Affero General Public License for more details.                       #
#                                                                             #
#   You should have received a copy of the GNU Affero General Public License  #
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.     #
#                                                                             #
###############################################################################

from openerp.osv.orm import Model
from base_external_referentials.external_osv import ExternalSession

class sale_shop(Model):
    _inherit='sale.shop'

    def _export_invoice_for_shop(self, cr, uid, external_session, shop, context=None):
        #Open the connection for pushing report
        external_session.file_session = ExternalSession(
                            external_session.referential_id.ext_file_referential_id,
                            external_session.sync_from_object,
                            )
        external_session.file_session.connection.persistant=True
        res = super(sale_shop, self)._export_invoice_for_shop(cr, uid, external_session, shop, context=context)
        #close the connection
        external_session.file_session.connection.close()
        return res
