# -*- encoding: utf-8 -*-
###############################################################################
#                                                                             #
#   Copyright (C) 2012 Akretion David BEAL <david.beal@akretion.com>
#   Copyright (C) 2012 Akretion Sébastien BEAU <sebastien.beau@akretion.com>
#   Copyright (C) 2014 Akretion  Chafique DELLI <chafique.delli@akretion.com>
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

import logging
import xmlrpclib
import base64

from openerp.osv import orm, fields
from openerp.addons.connector.exception import IDMissingInBackend
from openerp.addons.connector.unit.mapper import (mapping,
                                                  only_create,
                                                  ImportMapper,
                                                  ExportMapper)
from openerp.addons.magentoerpconnect.unit.binder import MagentoModelBinder
from openerp.addons.magentoerpconnect.unit.backend_adapter import GenericAdapter
from openerp.addons.magentoerpconnect.unit.import_synchronizer import (DelayedBatchImport,
                                                                       MagentoImportSynchronizer,
                                                                       AddCheckpoint)
from openerp.addons.magentoerpconnect.unit.export_synchronizer import MagentoExporter
from openerp.addons.magentoerpconnect.backend import magento
from openerp.addons.connector.queue.job import job
from openerp.addons.magentoerpconnect.connector import get_environment
from openerp.addons.connector.event import on_record_create

_logger = logging.getLogger(__name__)


class crm_claim(orm.Model):
    _inherit = "crm.claim"

    _columns = {
        'magento_bind_ids': fields.one2many(
            'magento.crm.claim', 'openerp_id',
            string="Magento Bindings"),
        'claim_line_ids': fields.one2many('claim.line',
                                                  'claim_id',
                                                  'Claim Lines'),
        'claim_comment_ids': fields.one2many('mail.message',
                                                  'claim_id',
                                                  'Claim Comments'),
        'claim_attachment_ids': fields.one2many('ir.attachment',
                                                  'claim_id',
                                                  'Claim Attachments'),
        'claim_id': fields.integer('Claim ID',
                                           help="'res_id' field in OpenErp"),
    }


class magento_crm_claim(orm.Model):
    _name = 'magento.crm.claim'
    _inherit = 'magento.binding'
    _description = 'Magento Claim'
    _inherits = {'crm.claim': 'openerp_id'}


    _columns = {
        'openerp_id': fields.many2one('crm.claim',
                                      string='Claim',
                                      required=True,
                                      ondelete='cascade'),
        'magento_claim_line_ids': fields.one2many('magento.claim.line',
                                                  'magento_claim_id',
                                                  'Magento Claim Lines'),
        'magento_claim_comment_ids': fields.one2many('magento.claim.comment',
                                                  'magento_claim_id',
                                                  'Magento Claim Comments'),
        'magento_claim_attachment_ids': fields.one2many('magento.claim.attachment',
                                                  'magento_claim_id',
                                                  'Magento Claim Attachments'),
        'magento_claim_id': fields.integer('Magento Claim ID',
                                           help="'rma_id' field in Magento"),
    }

    _sql_constraints = [
        ('magento_uniq', 'unique(backend_id, magento_id)',
         'A Claim with the same ID on Magento already exists.'),
    ]


class claim_line(orm.Model):
    _inherit = "claim.line"

    _columns = {
        'magento_bind_ids': fields.one2many(
                'magento.claim.line', 'openerp_id',
                string="Magento Bindings"),
        'claim_id': fields.many2one('crm.claim',
                                            string='Claim',
                                            ondelete='cascade'),
        'order_line_id': fields.many2one('sale.order.line', 'Order Line',
                                         help="The sale order line related to the "
                                           "returned product"),
        'sequence': fields.integer('Sequence',
                                   help="Gives the sequence "
                                   "of this line when displaying the claim."),
    }


class magento_claim_line(orm.Model):
    _name = 'magento.claim.line'
    _inherit = 'magento.binding'
    _description = 'Magento Claim Line'
    _inherits = {'claim.line': 'openerp_id'}

    def _get_lines_from_claim(self, cr, uid, ids, context=None):
        line_obj = self.pool.get('magento.claim.line')
        return line_obj.search(cr, uid,
                               [('magento_claim_id', 'in', ids)],
                               context=context)
    _columns = {
        'openerp_id': fields.many2one('claim.line',
                                      string='Claim Line',
                                      required=True,
                                      ondelete='cascade'),
        'magento_claim_id': fields.many2one('magento.crm.claim',
                                            string='Magento Claim',
                                            ondelete='cascade'),
        'backend_id': fields.related(
            'magento_claim_id', 'backend_id',
             type='many2one',
             relation='magento.backend',
             string='Magento Backend',
             store={'magento.claim.line':
                        (lambda self, cr, uid, ids, c=None: ids,
                         ['magento_claim_id'],
                         10),
                 'magento.crm.claim':
                     (_get_lines_from_claim, ['backend_id'], 20),
                   },
             readonly=True),
        }

    _sql_constraints = [
        ('magento_uniq', 'unique(backend_id, magento_id)',
         'A Claim Line with the same ID on Magento already exists.'),
    ]

    def create(self, cr, uid, vals, context=None):
        magento_claim_id = vals['magento_claim_id']
        info = self.pool['magento.crm.claim'].read(cr, uid,
                                                    [magento_claim_id],
                                                    ['openerp_id','description'],
                                                    context=context)
        claim_id = info[0]['openerp_id']
        descr = info[0]['description']
        vals['claim_id'] = claim_id[0]
        vals['claim_descr'] = descr
        return super(magento_claim_line, self).create(cr, uid, vals,
                                                           context=context)


class mail_message(orm.Model):
    _inherit = "mail.message"

    _columns = {
        'magento_claim_bind_ids': fields.one2many(
                'magento.claim.comment', 'openerp_id',
                string="Magento Bindings"),
        'claim_id': fields.many2one('crm.claim',
                                            string='Claim',
                                            ondelete='cascade'),
    }


class magento_claim_comment(orm.Model):
    _name = 'magento.claim.comment'
    _inherit = 'magento.binding'
    _description = 'Magento Claim Comment'
    _inherits = {'mail.message': 'openerp_id'}

    def _get_comments_from_claim(self, cr, uid, ids, context=None):
        comment_obj = self.pool.get('magento.claim.comment')
        return comment_obj.search(cr, uid,
                               [('magento_claim_id', 'in', ids)],
                               context=context)

    _columns = {
        'openerp_id': fields.many2one('mail.message',
                                      string='Claim Comment',
                                      required=True,
                                      ondelete='cascade'),
        'magento_claim_id': fields.many2one('magento.crm.claim',
                                            string='Magento Claim',
                                            ondelete='cascade'),
        'backend_id': fields.related(
            'magento_claim_id', 'backend_id',
             type='many2one',
             relation='magento.backend',
             string='Magento Backend',
             store={'magento.claim.comment':
                        (lambda self, cr, uid, ids, c=None: ids,
                         ['magento_claim_id'],
                         10),
                 'magento.crm.claim':
                     (_get_comments_from_claim, ['backend_id'], 20),
                   },
             readonly=True),

        }

    _sql_constraints = [
        ('magento_uniq', 'unique(backend_id, magento_id)',
         'A Claim Comment with the same ID on Magento already exists.'),
    ]

    def create(self, cr, uid, vals, context=None):
        magento_claim_id = vals['magento_claim_id']
        info = self.pool['magento.crm.claim'].read(cr, uid,
                                                    [magento_claim_id],
                                                    ['openerp_id'],
                                                    context=context)
        claim_id = info[0]['openerp_id'][0]
        claim = self.pool['crm.claim'].browse(cr, uid, claim_id, context=context)
        vals['claim_id'] = claim_id
        vals['res_id'] = claim_id
        vals['model'] = 'crm.claim'
        vals['subject'] = 'Sale Order ' + claim.ref.name
        return super(magento_claim_comment, self).create(cr, uid, vals,
                                                           context=context)


class ir_attachment(orm.Model):
    _inherit = "ir.attachment"

    _columns = {
        'magento_claim_bind_ids': fields.one2many(
                'magento.claim.attachment', 'openerp_id',
                string="Magento Bindings"),
        'claim_id': fields.many2one('crm.claim',
                                            string='Claim',
                                            ondelete='cascade'),
        'attachment_type': fields.selection(
            [('customer','Customer'),('seller','Seller')],
            'Attachment Type'),
    }


class magento_claim_attachment(orm.Model):
    _name = 'magento.claim.attachment'
    _inherit = 'magento.binding'
    _description = 'Magento Claim Attachment'
    _inherits = {'ir.attachment': 'openerp_id'}

    def _get_attachments_from_claim(self, cr, uid, ids, context=None):
        attachment_obj = self.pool.get('magento.claim.attachment')
        return attachment_obj.search(cr, uid,
                               [('magento_claim_id', 'in', ids)],
                               context=context)

    _columns = {
        'openerp_id': fields.many2one('ir.attachment',
                                      string='Claim Attachment',
                                      required=True,
                                      ondelete='cascade'),
        'magento_claim_id': fields.many2one('magento.crm.claim',
                                            string='Magento Claim',
                                            ondelete='cascade'),
        'backend_id': fields.related(
            'magento_claim_id', 'backend_id',
             type='many2one',
             relation='magento.backend',
             string='Magento Backend',
             store={'magento.claim.attachment':
                        (lambda self, cr, uid, ids, c=None: ids,
                         ['magento_claim_id'],
                         10),
                 'magento.crm.claim':
                     (_get_attachments_from_claim, ['backend_id'], 20),
                   },
             readonly=True),

        }

    _sql_constraints = [
        ('magento_uniq', 'unique(backend_id, magento_id)',
         'A Claim Attachment with the same ID on Magento already exists.'),
    ]

    def create(self, cr, uid, vals, context=None):
        magento_claim_id = vals['magento_claim_id']
        info = self.pool['magento.crm.claim'].read(cr, uid,
                                                    [magento_claim_id],
                                                    ['openerp_id'],
                                                    context=context)
        claim_id = info[0]['openerp_id'][0]
        vals['claim_id'] = claim_id
        vals['res_id'] = claim_id
        vals['res_model'] = 'crm.claim'
        return super(magento_claim_attachment, self).create(cr, uid, vals,
                                                           context=context)


@magento
class CrmClaimAdapter(GenericAdapter):
    _model_name = ['magento.crm.claim']
    _magento_model = 'rma'

    def _call(self, method, arguments):
        try:
            return super(CrmClaimAdapter, self)._call(method, arguments)
        except xmlrpclib.Fault as err:
            # this is the error in the Magento API
            # when the claim does not exist
            if err.faultCode == 100:
                raise IDMissingInBackend
            else:
                raise

    def search(self, filters=None, from_date=None):
        """ Search records according to some criterias
        and returns a list of ids

        :rtype: list
        """
        if filters is None:
            filters = {}
        if from_date is not None:
            filters = from_date.strftime('%Y-%m-%d %H:%M:%S')
        return [int(row['rma_id']) for row
                in self._call('%s.list' % self._magento_model,
                              [filters] if filters else [{}])]

    def read(self, id, storeview_id=None, attributes=None):
        """ Returns the information of a record

        :rtype: dict
        """
        return self._call('%s.get' % self._magento_model,
                          [int(id), storeview_id, attributes, 'id'])


@magento
class ClaimCommentAdapter(GenericAdapter):
    _model_name = ['magento.claim.comment']
    _magento_model = 'rma_comment'

    def _call(self, method, arguments):
        try:
            return super(ClaimCommentAdapter, self)._call(method, arguments)
        except xmlrpclib.Fault as err:
            # this is the error in the Magento API
            # when the claim does not exist
            if err.faultCode == 100:
                raise IDMissingInBackend
            else:
                raise

    def search_read(self, filters=None, from_date=None):
        """ Search records according to some criterias
        and returns their information
        """
        backend = self.session.browse('magento.backend', self.backend_record.id)
        if filters is None:
            filters = {}
        if from_date is not None:
            filters = from_date.strftime('%Y-%m-%d %H:%M:%S')
        elif backend:
            filters = backend.import_claims_from_date
        return self._call('%s.list' % self._magento_model,
                          [filters,1] if filters else [{},1])

    def read(self, magento_record, attributes=None):
        """ Returns the information of a record

        :rtype: dict
        """
        return magento_record


    def create(self, is_customer, message, created_at, rma_id):
        """ Create a claim comment on the external system """
        return self._call('%s.create' % self._magento_model,
                          [{'is_customer': is_customer,
                           'message': message,
                           'created_at': str(created_at),
                           'rma_id': str(rma_id)}])


@magento
class ClaimAttachmentAdapter(GenericAdapter):
    _model_name = ['magento.claim.attachment']
    _magento_model = 'rma_attachment'

    def _call(self, method, arguments):
        try:
            return super(ClaimAttachmentAdapter, self)._call(method, arguments)
        except xmlrpclib.Fault as err:
            # this is the error in the Magento API
            # when the claim does not exist
            if err.faultCode == 100:
                raise IDMissingInBackend
            else:
                raise

    def search_read(self, filters=None, from_date=None):
        """ Search records according to some criterias
        and returns their information
        """
        backend = self.session.browse('magento.backend', self.backend_record.id)
        if filters is None:
            filters = {}
        if from_date is not None:
            filters = from_date.strftime('%Y-%m-%d %H:%M:%S')
        elif backend:
            filters = backend.import_claims_from_date
        return self._call('%s.list' % self._magento_model,
                          [filters,1] if filters else [{},1])

    def read(self, magento_record, attributes=None):
        """ Returns the information of a record

        :rtype: dict
        """
        return magento_record

    def create(self, name, is_customer, created_at, rma_id, message):
        """ Create a claim attachment on the external system """
        return self._call('%s.create' % self._magento_model,
                          [{'name': str(name),
                            'is_customer': is_customer,
                            'created_at': str(created_at),
                            'rma_id': str(rma_id),
                            'content': str(message)}])


@magento
class CrmClaimBatchImport(DelayedBatchImport):
    """ Import the Magento Claims.

    For every claim in the list, a delayed job is created.
    Import from a date
    """
    _model_name = ['magento.crm.claim']

    def _import_record(self, record_id, **kwargs):
        """ Import the record directly """
        return super(CrmClaimBatchImport, self)._import_record(
            record_id, max_retries=0, priority=5)

    def run(self, filters=None):
        """ Run the synchronization """
        from_date = filters.pop('from_date', None)
        record_ids = self.backend_adapter.search(filters, from_date)
        _logger.info('search for magento claims %s returned %s',
                     from_date.strftime('%Y-%m-%d %H:%M:%S'), record_ids)
        for record_id in record_ids:
            self._import_record(record_id)


@magento
class CrmClaimImport(MagentoImportSynchronizer):
    _model_name = ['magento.crm.claim']

    def _import_dependencies(self):
        record = self.magento_record
        order_binder = self.get_binder_for_model('magento.sale.order')
        order_importer = self.get_connector_unit_for_model(MagentoImportSynchronizer,
                                                          'magento.sale.order')
        if order_binder.to_openerp(record['order_increment_id']) is None:
            order_importer.run(record['order_increment_id'])

    def _create(self, data):
        openerp_binding_id = super(CrmClaimImport, self)._create(data)
        checkpoint = self.get_connector_unit_for_model(AddCheckpoint)
        checkpoint.run(openerp_binding_id)
        return openerp_binding_id


@magento
class ClaimCommentBatchImport(DelayedBatchImport):
    """ Import the Magento Claim Comments from a date.
    """
    _model_name = ['magento.claim.comment']

    def _import_record(self, record, **kwargs):
        """ Import the record directly """
        return super(ClaimCommentBatchImport, self)._import_record(
            record, max_retries=0, priority=5)

    def run(self, filters=None):
        """ Run the synchronization """
        record_ids = []
        index = 0
        from_date = filters.pop('from_date', None)
        records = self.backend_adapter.search_read(filters, from_date)
        for record in records:
            record_ids += int(records[index]['rma_comment_id']),
            index += 1
            record['message'] = record['message'].encode('utf-8')
            self._import_record(record)
        _logger.info('search for magento claim comments from %s returned %s',
                     from_date.strftime('%Y-%m-%d %H:%M:%S'), record_ids)


@magento
class ClaimCommentImport(MagentoImportSynchronizer):
    _model_name = ['magento.claim.comment']

    def _import_dependencies(self):
        record = self.magento_record
        claim_binder = self.get_binder_for_model('magento.crm.claim')
        claim_importer = self.get_connector_unit_for_model(MagentoImportSynchronizer,
                                                          'magento.crm.claim')
        if claim_binder.to_openerp(record['rma_id']) is None:
            claim_importer.run(record['rma_id'])

    def _create(self, data):
        #we test whether the comment already exists in 'magento.claim.comment'
        #it may have been created during the import dependencies (RMA import)
        openerp_binding_id = False
        if 'magento_id' in data and data.get('magento_id'):
            openerp_binding_id = self.session.search(self.model._name,
                                                  [('magento_id', '=', data['magento_id'])])
        if not openerp_binding_id:
            openerp_binding_id = super(ClaimCommentImport, self)._create(data)
            checkpoint = self.get_connector_unit_for_model(AddCheckpoint)
            checkpoint.run(openerp_binding_id)
        else:
            openerp_binding_id = openerp_binding_id[0]
        return openerp_binding_id


@magento
class ClaimAttachmentBatchImport(DelayedBatchImport):
    """ Import the Magento Claim Attachments from a date.
    """
    _model_name = ['magento.claim.attachment']

    def _import_record(self, record, **kwargs):
        """ Import the record directly """
        return super(ClaimAttachmentBatchImport, self)._import_record(
            record, max_retries=0, priority=5)

    def run(self, filters=None):
        """ Run the synchronization """
        record_ids = []
        index = 0
        from_date = filters.pop('from_date', None)
        records = self.backend_adapter.search_read(filters, from_date)
        for record in records:
            record_ids += int(records[index]['rma_attachment_id']),
            index += 1
            self._import_record(record)
        _logger.info('search for magento claim attachments from %s returned %s',
                     from_date.strftime('%Y-%m-%d %H:%M:%S'), record_ids)


@magento
class ClaimAttachmentImport(MagentoImportSynchronizer):
    _model_name = ['magento.claim.attachment']

    def _import_dependencies(self):
        record = self.magento_record
        claim_binder = self.get_binder_for_model('magento.crm.claim')
        claim_importer = self.get_connector_unit_for_model(MagentoImportSynchronizer,
                                                          'magento.crm.claim')
        if claim_binder.to_openerp(record['rma_id']) is None:
            claim_importer.run(record['rma_id'])

    def _create(self, data):
        #we test whether the attachment already exists in 'magento.claim.attachment'
        #it may have been created during the import dependencies (RMA import)
        openerp_binding_id = False
        if 'magento_id' in data and data.get('magento_id'):
            openerp_binding_id = self.session.search(self.model._name,
                                                     [('magento_id', '=', data['magento_id'])])
        if not openerp_binding_id:
            openerp_binding_id = super(ClaimAttachmentImport, self)._create(data)
            checkpoint = self.get_connector_unit_for_model(AddCheckpoint)
            checkpoint.run(openerp_binding_id)
        else:
            openerp_binding_id = openerp_binding_id[0]
        return openerp_binding_id



@magento
class CrmClaimImportMapper(ImportMapper):
    _model_name = 'magento.crm.claim'

    direct = [('rma_id', 'number'),
              ('subject', 'name'),
              ('description', 'description'),
              ('created_at', 'date'),
              ]

    children = [('items', 'magento_claim_line_ids', 'magento.claim.line'),
                ('comments', 'magento_claim_comment_ids', 'magento.claim.comment'),
                ('attachments', 'magento_claim_attachment_ids', 'magento.claim.attachment'),
                ]


    def _map_child(self, map_record, from_attr, to_attr, model_name):
        if from_attr in map_record.source:
            return super(CrmClaimImportMapper, self)._map_child(map_record,
                                                                from_attr,
                                                                to_attr,
                                                                model_name)

    @mapping
    def partner_id(self, record):
        partner_ids = self.session.search('magento.res.partner',
                                        [['magento_id', '=', record['customer_id']]])
        partner = self.session.browse('magento.res.partner', partner_ids[0])
        partner_id = partner.openerp_id.id
        address = self.session.browse('res.partner', partner_id)
        return {'partner_id': partner_id,
                'email_from': address.email,
                'partner_phone': address.phone}

    @mapping
    def ref(self, record):
        order_ids = self.session.search('sale.order',
                                        [['name', '=', record['order_increment_id']]])
        if order_ids:
            ref = 'sale.order,' + str(order_ids[0])
            return {'ref': ref}

    @mapping
    def state(self, record):
        state = 'draft'
        return {'state': state}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}

@magento
class ClaimLineImportMapper(ImportMapper):
    _model_name = 'magento.claim.line'

    direct = [('qty', 'product_returned_quantity'),]

    @mapping
    def name(self, record):
        order_line_ids = self.session.search('magento.sale.order.line',
                                        [['magento_id', '=', record['order_item_id']]])
        order_line = self.session.browse('magento.sale.order.line', order_line_ids[0])
        order_name  = order_line.magento_order_id.magento_id
        return {'name': order_name}

    @mapping
    def order_line_id(self, record):
        order_line_ids = self.session.search('magento.sale.order.line',
                                        [['magento_id', '=', record['order_item_id']]])
        order_line = self.session.browse('magento.sale.order.line', order_line_ids[0])
        order_line_id  = order_line.openerp_id.id
        return {'order_line_id': order_line_id}

    @mapping
    def product_id(self, record):
        order_line_ids = self.session.search('magento.sale.order.line',
                                        [['magento_id', '=', record['order_item_id']]])
        order_line = self.session.browse('magento.sale.order.line', order_line_ids[0])
        product_id  = order_line.openerp_id.product_id.id
        return {'product_id': product_id}

    @mapping
    def claim_origine(self, record):
        claim_origine = 'other'
        return {'claim_origine': claim_origine}

    @mapping
    def magento_id(self, record):
        return {'magento_id': record['rma_item_id']}


@magento
class ClaimCommentImportMapper(ImportMapper):
    _model_name = 'magento.claim.comment'

    direct = [
        ('message', 'body'),
        ('created_at','date')
        ]

    @mapping
    def subtype_id(self, record):
        if record['is_customer']=='1':
            subtype_id = False
            return {'subtype_id': subtype_id}

    @mapping
    def type(self, record):
        type = 'comment'
        return {'type': type}

    @mapping
    def magento_id(self, record):
        return {'magento_id': record['rma_comment_id']}

    @mapping
    def magento_claim_id(self, record):
        magento_claim_ids = self.session.search('magento.crm.claim',
                                                [('magento_id', '=',int(record['rma_id']))])
        if magento_claim_ids:
            claim_id = magento_claim_ids[0]
            return {'magento_claim_id': claim_id}


@magento
class ClaimAttachmentImportMapper(ImportMapper):
    _model_name = 'magento.claim.attachment'

    direct = [
        ('name','name'),
        ('name', 'datas_fname'),
        ('created_at','create_date')
        ]

    @mapping
    def type(self, record):
        type = 'binary'
        return {'type': type}

    @mapping
    def db_datas(self, record):
        data = base64.b64decode(base64.b64encode(record['content']))
        return {'db_datas': data}

    @mapping
    def attachment_type(self, record):
        if record['is_customer']=='1':
            attachment_type = 'customer'
            return {'attachment_type': attachment_type}

    @mapping
    def magento_id(self, record):
        return {'magento_id': record['rma_attachment_id']}

    @mapping
    def magento_claim_id(self, record):
        magento_claim_ids = self.session.search('magento.crm.claim',
                                                [('magento_id', '=',int(record['rma_id']))])
        if magento_claim_ids:
            claim_id = magento_claim_ids[0]
            return {'magento_claim_id': claim_id}


@job
def crm_claim_import_batch(session, model_name, backend_id, filters=None):
    """ Prepare a batch import of claims from Magento """
    if filters is None:
        filters = {}
    assert 'magento_storeview_id' in filters, 'Missing information about Magento Storeview'
    env = get_environment(session, model_name, backend_id)
    importer = env.get_connector_unit(CrmClaimBatchImport)
    importer.run(filters)


@job
def claim_comment_import_batch(session, model_name, backend_id, filters=None):
    """ Prepare a batch import of claim comments from Magento """
    if filters is None:
        filters = {}
    assert 'magento_storeview_id' in filters, 'Missing information about Magento Storeview'
    env = get_environment(session, model_name, backend_id)
    importer = env.get_connector_unit(ClaimCommentBatchImport)
    importer.run(filters)


@job
def claim_attachment_import_batch(session, model_name, backend_id, filters=None):
    """ Prepare a batch import of claim attachments from Magento """
    if filters is None:
        filters = {}
    assert 'magento_storeview_id' in filters, 'Missing information about Magento Storeview'
    env = get_environment(session, model_name, backend_id)
    importer = env.get_connector_unit(ClaimAttachmentBatchImport)
    importer.run(filters)


@magento
class MagentoClaimCommentExporter(MagentoExporter):
    """ Export claim comments seller to Magento """
    _model_name = ['magento.claim.comment']

    def _should_import(self):
        return False

    def _create(self, data):
        """ Create the Magento record """
        # special check on data before export
        self._validate_data(data)
        return self.backend_adapter.create(data['is_customer'],
                                           data['message'],
                                           data['created_at'],
                                           data['rma_id'])


@on_record_create(model_names='mail.message')
def comment_create_bindings(session, model_name, record_id, vals):
    """
    Create a ``magento.claim.comment`` record. This record will then
    be exported to Magento.
    """
    comment = session.browse(model_name, record_id)
    subtype_ids = session.search('mail.message.subtype',
                             [['name', '=', 'Discussions']])
    magento_claim = session.search('magento.crm.claim',
                                   [['openerp_id', '=', comment.res_id]])
    if comment.type == 'comment' and comment.subtype_id.id == subtype_ids[0] and vals['model'] == 'crm.claim' and magento_claim:
        claim = session.browse('crm.claim', comment.res_id)
        for magento_claim in claim.magento_bind_ids:
            session.create('magento.claim.comment',
                           {'backend_id': magento_claim.backend_id.id,
                            'openerp_id': comment.id,
                            'magento_claim_id': magento_claim.id})


@on_record_create(model_names='magento.claim.comment')
def delay_export_claim_comment(session, model_name, record_id, vals):
    """
    Delay the job to export the magento claim comment.
    """
    magento_comment = session.browse(model_name, record_id)
    subtype_ids = session.search('mail.message.subtype',
                             [['name', '=', 'Discussions']])
    if magento_comment.openerp_id.type == 'comment' and magento_comment.openerp_id.subtype_id.id == subtype_ids[0]:
        export_claim_comment.delay(session, model_name, record_id)


@magento
class ClaimCommentExportMapper(ExportMapper):
    _model_name = 'magento.claim.comment'

    @only_create
    @mapping
    def is_customer(self, record):
        return {'is_customer': '0'}

    @only_create
    @mapping
    def created_at(self, record):
        return {'created_at': str(record.date)}

    @only_create
    @mapping
    def message(self, record):
        return {'message': str(record.body)}

    @only_create
    @mapping
    def rma_id(self, record):
        return {'rma_id': str(record.magento_claim_id.magento_id)}


@job
def export_claim_comment(session, model_name, record_id):
    """ Export a claim comment. """
    comment = session.browse(model_name, record_id)
    backend_id = comment.backend_id.id
    env = get_environment(session, model_name, backend_id)
    comment_exporter = env.get_connector_unit(MagentoClaimCommentExporter)
    return comment_exporter.run(record_id)


@magento
class MagentoClaimAttachmentExporter(MagentoExporter):
    """ Export claim attachments seller to Magento """
    _model_name = ['magento.claim.attachment']

    def _should_import(self):
        return False

    def _create(self, data):
        """ Create the Magento record """
        # special check on data before export
        self._validate_data(data)
        return self.backend_adapter.create(data['name'],
                                           data['is_customer'],
                                           data['created_at'],
                                           data['rma_id'],
                                           data['content'])


@on_record_create(model_names='ir.attachment')
def attachment_create_bindings(session, model_name, record_id, vals):
    """
    Create a ``magento.claim.attachment`` record. This record will then
    be exported to Magento.
    """
    attachment = session.browse(model_name, record_id)
    magento_claim = session.search('magento.crm.claim',
                                   [['openerp_id', '=', attachment.res_id]])
    if attachment.attachment_type == False  and vals['res_model'] == 'crm.claim' and magento_claim:
        claim = session.browse('crm.claim', attachment.res_id)
        for magento_claim in claim.magento_bind_ids:
            session.create('magento.claim.attachment',
                           {'backend_id': magento_claim.backend_id.id,
                            'openerp_id': attachment.id,
                            'magento_claim_id': magento_claim.id})


@on_record_create(model_names='magento.claim.attachment')
def delay_export_claim_attachment(session, model_name, record_id, vals):
    """
    Delay the job to export the magento claim attachment.
    """
    magento_attachment = session.browse(model_name, record_id)
    if magento_attachment.openerp_id.attachment_type == False :
        export_claim_attachment.delay(session, model_name, record_id)

@magento
class ClaimAttachmentExportMapper(ExportMapper):
    _model_name = 'magento.claim.attachment'

    @only_create
    @mapping
    def name(self, record):
        return {'name': str(record.name)}

    @only_create
    @mapping
    def is_customer(self, record):
        return {'is_customer': '0'}

    @only_create
    @mapping
    def created_at(self, record):
        return {'created_at': str(record.create_date)}

    @only_create
    @mapping
    def content(self, record):
        attachment = record['openerp_id']
        data = base64.b64decode(base64.b64encode(attachment.db_datas))
        return {'content': data}

    @only_create
    @mapping
    def rma_id(self, record):
        return {'rma_id': str(record.magento_claim_id.magento_id)}


@job
def export_claim_attachment(session, model_name, record_id):
    """ Export a claim attachment. """
    attachment = session.browse(model_name, record_id)
    backend_id = attachment.backend_id.id
    env = get_environment(session, model_name, backend_id)
    attachment_exporter = env.get_connector_unit( MagentoClaimAttachmentExporter)
    return attachment_exporter.run(record_id)


@magento
class MagentoClaimBinder(MagentoModelBinder):

    _model_name = [
        'magento.crm.claim',
        'magento.claim.line',
        ]

@magento
class MagentoClaimCommentBinder(MagentoModelBinder):

    _model_name = [
        'magento.claim.comment',
        ]

    def bind(self, external_id, binding_id):
        if isinstance(external_id, dict) and external_id.get('rma_comment_id'):
            external_id = external_id['rma_comment_id']
        return super(MagentoClaimCommentBinder, self).bind(external_id, binding_id)


@magento
class MagentoClaimAttachmentBinder(MagentoModelBinder):

    _model_name = [
        'magento.claim.attachment',
        ]

    def bind(self, external_id, binding_id):
        if isinstance(external_id, dict) and external_id.get('rma_attachment_id'):
            external_id = external_id['rma_attachment_id']
        return super(MagentoClaimAttachmentBinder, self).bind(external_id, binding_id)

@magento
class CrmClaimAddCheckpoint(AddCheckpoint):

    _model_name = [
        'magento.crm.claim',
        'magento.claim.line',
        'magento.claim.comment',
        'magento.claim.attachment'
        ]
