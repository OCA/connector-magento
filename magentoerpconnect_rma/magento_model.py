# -*- coding: utf-8 -*-
from openerp.osv import orm, fields


class magento_backend(orm.Model):
    _inherit = 'magento.backend'

    _columns = {
        'import_claims_from_date': fields.datetime('Import claims from date'),
        }

    def import_claim(self, cr, uid, ids, context=None):
        self._import_from_date(cr, uid, ids, 'magento.crm.claim',
                               'import_claims_from_date', context=context)
        return True

    def _scheduler_import_crm_claims(self, cr, uid, domain=None, context=None):
        self._magento_backend(cr, uid, self.import_claim,
                              domain=domain, context=context)

    
