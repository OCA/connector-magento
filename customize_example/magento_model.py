# -*- coding: utf-8 -*-
from openerp.osv import orm, fields


class magento_backend(orm.Model):
    _inherit = 'magento.backend'

    def _select_versions(self, cr, uid, context=None):
        """ Available versions

        Can be inherited to add custom versions.
        """
        versions = super(magento_backend, self)._select_versions(cr, uid, context=context)
        versions.append(('1.7-myversion', '1.7 My Version'))
        return versions

    _columns = {
        'version': fields.selection(
            _select_versions,
            string='Version',
            required=True),
        }
