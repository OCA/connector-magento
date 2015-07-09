# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2014 initOS GmbH & Co. KG (<http://www.initos.com>).
#    Author Katja Matthes <katja.matthes at initos.com>
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


class magento_backend(orm.Model):
    _inherit = 'magento.backend'

    def _select_versions(self, cr, uid, context=None):
        """ Make new version selectable.
        """
        versions = super(magento_backend, self)._select_versions(cr, uid, context=context)
        versions.append(('1.7-bundle-import-childs', '1.7 - Bundle Import Child Items'))
        return versions

    _columns = {
        'version': fields.selection(_select_versions, string='Version', required=True),
    }
