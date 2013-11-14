# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright 2013
#    Author: Guewen Baconnier - Camptocamp
#            David Béal - Akretion
#            Sébastien Beau - Akretion
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

import logging
from openerp.osv import orm, fields
from openerp.addons.connector.session import ConnectorSession
from openerp.addons.magentoerpconnect.unit.import_synchronizer import import_batch


_logger = logging.getLogger(__name__)


class magento_backend(orm.Model):
    _inherit = 'magento.backend'

    def import_attribute_sets(self, cr, uid, ids, context=None):
        if not hasattr(ids, '__iter__'):
            ids = [ids]
        self.check_magento_structure(cr, uid, ids, context=context)
        session = ConnectorSession(cr, uid, context=context)
        for backend_id in ids:
            import_batch.delay(session, 'magento.attribute.set', backend_id)
        return True

    _columns = {
        'attribute_set_tpl_id': fields.many2one(
            'magento.attribute.set',
            'Attribute set template',
            help="Attribute set ID basing on which the new attribute set "
            "will be created. \nIf no value, 'Default' attribute set name "
            "will be used."),
    }
