# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: David BEAL Copyright 2014 Akretion
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

from openerp.osv import orm, fields
from openerp.tools.translate import _


class magento_store(orm.Model):
    _inherit = 'magento.store'

    _columns = {
        'send_sale_comment_mail': fields.boolean(
            'Send email notification on sale comment',
            help=_("Require Magento to send email on 'sale order comment' "
                   "based on 'send a message' case (not 'log a note')")),
    }

    _defaults = {
        'send_sale_comment_mail': False,
    }
