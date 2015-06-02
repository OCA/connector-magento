# -*- coding: utf-8 -*-
from openerp.osv import orm, fields


class magento_backend(orm.Model):
    _inherit = 'magento.backend'

    _columns = {
        'import_claims_from_date': fields.datetime('Import claims from date'),
        'import_claim_comments_from_date': fields.datetime(
            'Import claim comments from date'),
        'import_claim_attachments_from_date': fields.datetime(
            'Import claim attachments from date'),
        }

    def import_claim(self, cr, uid, ids, context=None):
        self._import_from_date(cr, uid, ids, 'magento.crm.claim',
                               'import_claims_from_date', context=context)
        return True

    def import_claim_comment(self, cr, uid, ids, context=None):
        self._import_from_date(cr, uid, ids, 'magento.claim.comment',
                               'import_claim_comments_from_date',
                               context=context)
        return True

    def import_claim_attachment(self, cr, uid, ids, context=None):
        self._import_from_date(cr, uid, ids, 'magento.claim.attachment',
                               'import_claim_attachments_from_date',
                               context=context)
        return True

    def _scheduler_import_crm_claims(self, cr, uid, domain=None, context=None):
        self._magento_backend(cr, uid, self.import_claim,
                              domain=domain, context=context)

    def _scheduler_import_claim_comments(
            self, cr, uid, domain=None, context=None):
        self._magento_backend(cr, uid, self.import_claim_comment,
                              domain=domain, context=context)

    def _scheduler_import_claim_attachments(
            self, cr, uid, domain=None, context=None):
        self._magento_backend(cr, uid, self.import_claim_attachment,
                              domain=domain, context=context)
