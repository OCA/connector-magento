# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Joel Grand-Guillaume
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

import logging
import xmlrpclib
from datetime import datetime, timedelta
import openerp.addons.decimal_precision as dp
from openerp.osv import fields, orm
from openerp.tools.translate import _
from openerp.addons.connector.connector import ConnectorUnit
from openerp.addons.connector.exception import (NothingToDoJob,
                                                FailedJobError,
                                                IDMissingInBackend)
from openerp.addons.connector.queue.job import job
from openerp.addons.connector.unit.mapper import (mapping,
                                                  ImportMapper
                                                  )
from openerp.addons.connector_ecommerce.unit.sale_order_onchange import (
    SaleOrderOnChange)
from openerp.addons.connector_ecommerce.sale import (ShippingLineBuilder,
                                                     CashOnDeliveryLineBuilder,
                                                     GiftOrderLineBuilder)
from .unit.backend_adapter import (GenericAdapter,
                                   MAGENTO_DATETIME_FORMAT,
                                   )
from .unit.import_synchronizer import (DelayedBatchImport,
                                       MagentoImportSynchronizer
                                       )
from .exception import OrderImportRuleRetry
from .backend import magento
from .connector import get_environment
from .partner import PartnerImportMapper

_logger = logging.getLogger(__name__)


ORDER_STATUS_MAPPING = {  # XXX check if still needed
    'manual': 'processing',
    'progress': 'processing',
    'shipping_except': 'complete',
    'invoice_except': 'complete',
    'done': 'complete',
    'cancel': 'canceled',
    'waiting_date': 'holded'
}


class magento_sale_order(orm.Model):
    _name = 'magento.sale.order'
    _inherit = 'magento.binding'
    _description = 'Magento Sale Order'
    _inherits = {'sale.order': 'openerp_id'}

    _columns = {
        'openerp_id': fields.many2one('sale.order',
                                      string='Sale Order',
                                      required=True,
                                      ondelete='cascade'),
        'magento_order_line_ids': fields.one2many('magento.sale.order.line',
                                                  'magento_order_id',
                                                  'Magento Order Lines'),
        # XXX common to all ecom sale orders
        'total_amount': fields.float(
            'Total amount',
            digits_compute=dp.get_precision('Account')),
        # XXX common to all ecom sale orders
        'total_amount_tax': fields.float(
            'Total amount w. tax',
            digits_compute=dp.get_precision('Account')),
        'magento_order_id': fields.integer('Magento Order ID',
                                           help="'order_id' field in Magento"),
        # when a sale order is modified, Magento creates a new one, cancels
        # the parent order and link the new one to the canceled parent
        'magento_parent_id': fields.many2one('magento.sale.order',
                                             string='Parent Magento Order'),
        'storeview_id': fields.many2one('magento.storeview',
                                        string='Magento Storeview'),
    }

    _sql_constraints = [
        ('magento_uniq', 'unique(backend_id, magento_id)',
         'A sale order line with the same ID on Magento already exists.'),
    ]


class sale_order(orm.Model):
    _inherit = 'sale.order'

    def get_parent_id(self, cr, uid, ids, context=None):
        """ Return the parent order.

        For Magento sales orders, the magento parent order is stored
        in the binding, get it from there.
        """
        res = super(sale_order, self).get_parent_id(cr, uid, ids,
                                                    context=context)
        for order in self.browse(cr, uid, ids, context=context):
            if not order.magento_bind_ids:
                continue
            # assume we only have 1 SO in OpenERP for 1 SO in Magento
            magento_order = order.magento_bind_ids[0]
            if magento_order.magento_parent_id:
                res[order.id] = magento_order.magento_parent_id.openerp_id.id
        return res

    _columns = {
        'magento_bind_ids': fields.one2many(
            'magento.sale.order', 'openerp_id',
            string="Magento Bindings"),
    }

    def copy_data(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default['magento_bind_ids'] = False
        return super(sale_order, self).copy_data(cr, uid, id,
                                                 default=default,
                                                 context=context)

    def copy_quotation(self, cr, uid, ids, context=None):
        if isinstance(ids, (tuple, list)):
            assert len(ids) == 1, ("1 ID expected, "
                                   "got the following list %s" % (ids,))
        if context is None:
            context = {}
        else:
            context = context.copy()
        context['__copy_from_quotation'] = True
        result = super(sale_order, self).copy_quotation(cr, uid, ids,
                                                        context=context)
        # link binding of the canceled order to the new order, so the
        # operations done on the new order will be sync'ed with Magento
        new_id = result['res_id']
        binding_obj = self.pool['magento.sale.order']
        binding_ids = binding_obj.search(cr, uid,
                                         [('openerp_id', '=', ids[0])],
                                         context=context)
        binding_obj.write(cr, uid, binding_ids,
                          {'openerp_id': new_id},
                          context=context)
        return result


class magento_sale_order_line(orm.Model):
    _name = 'magento.sale.order.line'
    _inherit = 'magento.binding'
    _description = 'Magento Sale Order Line'
    _inherits = {'sale.order.line': 'openerp_id'}

    def _get_lines_from_order(self, cr, uid, ids, context=None):
        line_obj = self.pool.get('magento.sale.order.line')
        return line_obj.search(cr, uid,
                               [('magento_order_id', 'in', ids)],
                               context=context)
    _columns = {
        'magento_order_id': fields.many2one('magento.sale.order',
                                            'Magento Sale Order',
                                            required=True,
                                            ondelete='cascade',
                                            select=True),
        'openerp_id': fields.many2one('sale.order.line',
                                      string='Sale Order Line',
                                      required=True,
                                      ondelete='cascade'),
        'backend_id': fields.related(
            'magento_order_id', 'backend_id',
            type='many2one',
            relation='magento.backend',
            string='Magento Backend',
            store={
                'magento.sale.order.line':
                (lambda self, cr, uid, ids, c=None: ids,
                 ['magento_order_id'],
                 10),
                'magento.sale.order':
                (_get_lines_from_order, ['backend_id'], 20),
            },
            readonly=True),
        'tax_rate': fields.float('Tax Rate',
                                 digits_compute=dp.get_precision('Account')),
        # XXX common to all ecom sale orders
        'notes': fields.char('Notes'),
        }

    _sql_constraints = [
        ('magento_uniq', 'unique(backend_id, magento_id)',
         'A sale order line with the same ID on Magento already exists.'),
    ]

    def create(self, cr, uid, vals, context=None):
        magento_order_id = vals['magento_order_id']
        info = self.pool['magento.sale.order'].read(cr, uid,
                                                    [magento_order_id],
                                                    ['openerp_id'],
                                                    context=context)
        order_id = info[0]['openerp_id']
        vals['order_id'] = order_id[0]
        return super(magento_sale_order_line, self).create(cr, uid, vals,
                                                           context=context)


class sale_order_line(orm.Model):
    _inherit = 'sale.order.line'
    _columns = {
        'magento_bind_ids': fields.one2many(
            'magento.sale.order.line', 'openerp_id',
            string="Magento Bindings"),
    }

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}

        old_line_id = None
        if context.get('__copy_from_quotation'):
            # when we are copying a sale.order from a canceled one,
            # the id of the copied line is inserted in the vals
            # in `copy_data`.
            old_line_id = vals.pop('__copy_from_line_id', None)
        new_id = super(sale_order_line, self).create(cr, uid, vals,
                                                     context=context)
        if old_line_id:
            # link binding of the canceled order lines to the new order
            # lines, happens when we are using the 'New Copy of
            # Quotation' button on a canceled sales order
            binding_obj = self.pool['magento.sale.order.line']
            binding_ids = binding_obj.search(
                cr, uid,
                [('openerp_id', '=', old_line_id)],
                context=context)
            if binding_ids:
                binding_obj.write(cr, uid, binding_ids,
                                  {'openerp_id': new_id},
                                  context=context)
        return new_id

    def copy_data(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        if context is None:
            context = {}

        default['magento_bind_ids'] = False
        data = super(sale_order_line, self).copy_data(cr, uid, id,
                                                      default=default,
                                                      context=context)
        if context.get('__copy_from_quotation'):
            # copy_data is called by `copy` of the sale.order which
            # builds a dict for the full new sale order, so we lose the
            # association between the old and the new line.
            # Keep a trace of the old id in the vals that will be passed
            # to `create`, from there, we'll be able to update the
            # Magento bindings, modifying the relation from the old to
            # the new line.
            data['__copy_from_line_id'] = id
        return data


@magento
class SaleOrderAdapter(GenericAdapter):
    _model_name = 'magento.sale.order'
    _magento_model = 'sales_order'
    _admin_path = '{model}/view/order_id/{id}'

    def _call(self, method, arguments):
        try:
            return super(SaleOrderAdapter, self)._call(method, arguments)
        except xmlrpclib.Fault as err:
            # this is the error in the Magento API
            # when the sales order does not exist
            if err.faultCode == 100:
                raise IDMissingInBackend
            else:
                raise

    def search(self, filters=None, from_date=None, to_date=None,
               magento_storeview_ids=None):
        """ Search records according to some criteria
        and returns a list of ids

        :rtype: list
        """
        if filters is None:
            filters = {}
        dt_fmt = MAGENTO_DATETIME_FORMAT
        if from_date is not None:
            filters.setdefault('created_at', {})
            filters['created_at']['from'] = from_date.strftime(dt_fmt)
        if to_date is not None:
            filters.setdefault('created_at', {})
            filters['created_at']['to'] = to_date.strftime(dt_fmt)
        if magento_storeview_ids is not None:
            filters['store_id'] = {'in': magento_storeview_ids}

        arguments = {'imported': False,
                     # 'limit': 200,
                     'filters': filters,
                     }
        return super(SaleOrderAdapter, self).search(arguments)

    def read(self, id, attributes=None):
        """ Returns the information of a record

        :rtype: dict
        """
        record = self._call('%s.info' % self._magento_model,
                            [id, attributes])
        return record

    def get_parent(self, id):
        return self._call('%s.get_parent' % self._magento_model, [id])


@magento
class SaleOrderBatchImport(DelayedBatchImport):
    _model_name = ['magento.sale.order']

    def _import_record(self, record_id, **kwargs):
        """ Import the record directly """
        return super(SaleOrderBatchImport, self)._import_record(
            record_id, max_retries=0, priority=5)

    def run(self, filters=None):
        """ Run the synchronization """
        if filters is None:
            filters = {}
        filters['state'] = {'neq': 'canceled'}
        from_date = filters.pop('from_date', None)
        to_date = filters.pop('to_date', None)
        magento_storeview_ids = [filters.pop('magento_storeview_id')]
        record_ids = self.backend_adapter.search(
            filters,
            from_date=from_date,
            to_date=to_date,
            magento_storeview_ids=magento_storeview_ids)
        _logger.info('search for magento saleorders %s returned %s',
                     filters, record_ids)
        for record_id in record_ids:
            self._import_record(record_id)


@magento
class SaleImportRule(ConnectorUnit):
    _model_name = ['magento.sale.order']

    def _rule_always(self, record, method):
        """ Always import the order """
        return True

    def _rule_never(self, record, method):
        """ Never import the order """
        raise NothingToDoJob('Orders with payment method %s '
                             'are never imported.' %
                             record['payment']['method'])

    def _rule_authorized(self, record, method):
        """ Import the order only if payment has been authorized. """
        if not record.get('payment', {}).get('base_amount_authorized'):
            raise OrderImportRuleRetry('The order has not been authorized.\n'
                                       'The import will be retried later.')

    def _rule_paid(self, record, method):
        """ Import the order only if it has received a payment """
        if not record.get('payment', {}).get('amount_paid'):
            raise OrderImportRuleRetry('The order has not been paid.\n'
                                       'The import will be retried later.')

    _rules = {'always': _rule_always,
              'paid': _rule_paid,
              'authorized': _rule_authorized,
              'never': _rule_never,
              }

    def _rule_global(self, record, method):
        """ Rule always executed, whichever is the selected rule """
        # the order has been canceled since the job has been created
        order_id = record['increment_id']
        if record['state'] == 'canceled':
            raise NothingToDoJob('Order %s canceled' % order_id)
        max_days = method.days_before_cancel
        if max_days:
            fmt = '%Y-%m-%d %H:%M:%S'
            order_date = datetime.strptime(record['created_at'], fmt)
            if order_date + timedelta(days=max_days) < datetime.now():
                raise NothingToDoJob('Import of the order %s canceled '
                                     'because it has not been paid since %d '
                                     'days' % (order_id, max_days))

    def check(self, record):
        """ Check whether the current sale order should be imported
        or not. It will actually use the payment method configuration
        and see if the choosed rule is fullfilled.

        :returns: True if the sale order should be imported
        :rtype: boolean
        """
        session = self.session
        payment_method = record['payment']['method']
        method_ids = session.search('payment.method',
                                    [('name', '=', payment_method)])
        if not method_ids:
            raise FailedJobError(
                "The configuration is missing for the Payment Method '%s'.\n\n"
                "Resolution:\n"
                "- Go to "
                "'Sales > Configuration > Sales > Customer Payment Method\n"
                "- Create a new Payment Method with name '%s'\n"
                "-Eventually  link the Payment Method to an existing Workflow "
                "Process or create a new one." % (payment_method,
                                                  payment_method))
        method = session.browse('payment.method', method_ids[0])

        self._rule_global(record, method)
        self._rules[method.import_rule](self, record, method)


@magento
class SaleOrderMoveComment(ConnectorUnit):
    _model_name = ['magento.sale.order']

    def move(self, binding):
        pass


@magento
class SaleOrderImport(MagentoImportSynchronizer):
    _model_name = ['magento.sale.order']

    @property
    def mapper(self):
        if self._mapper is None:
            self._mapper = self.environment.get_connector_unit(
                SaleOrderImportMapper)
        return self._mapper

    def _must_skip(self):
        """ Hook called right after we read the data from the backend.

        If the method returns a message giving a reason for the
        skipping, the import will be interrupted and the message
        recorded in the job (if the import is called directly by the
        job, not by dependencies).

        If it returns None, the import will continue normally.

        :returns: None | str | unicode
        """
        if self.binder.to_openerp(self.magento_id):
            return _('Already imported')

    def _clean_magento_items(self, resource):
        """
        Method that clean the sale order line given by magento before
        importing it

        This method has to stay here because it allow to customize the
        behavior of the sale order.

        """
        child_items = {}  # key is the parent item id
        top_items = []

        # Group the childs with their parent
        for item in resource['items']:
            if item.get('parent_item_id'):
                child_items.setdefault(item['parent_item_id'], []).append(item)
            else:
                top_items.append(item)

        all_items = []
        for top_item in top_items:
            if top_item['item_id'] in child_items:
                item_modified = self._merge_sub_items(
                    top_item['product_type'], top_item,
                    child_items[top_item['item_id']])
                if not isinstance(item_modified, list):
                    item_modified = [item_modified]
                all_items.extend(item_modified)
            else:
                all_items.append(top_item)
        resource['items'] = all_items
        return resource

    def _merge_sub_items(self, product_type, top_item, child_items):
        """
        Manage the sub items of the magento sale order lines. A top item
        contains one or many child_items. For some product types, we
        want to merge them in the main item, or keep them as order line.

        This method has to stay because it allow to customize the
        behavior of the sale order according to the product type.

        A list may be returned to add many items (ie to keep all
        child_items as items.

        :param top_item: main item (bundle, configurable)
        :param child_items: list of childs of the top item
        :return: item or list of items
        """
        if product_type == 'configurable':
            item = top_item.copy()
            # For configurable product all information regarding the
            # price is in the configurable item. In the child a lot of
            # information is empty, but contains the right sku and
            # product_id. So the real product_id and the sku and the name
            # have to be extracted from the child
            for field in ['sku', 'product_id', 'name']:
                item[field] = child_items[0][field]
            return item
        return top_item

    def _import_customer_group(self, group_id):
        binder = self.get_binder_for_model('magento.res.partner.category')
        if binder.to_openerp(group_id) is None:
            importer = self.get_connector_unit_for_model(
                MagentoImportSynchronizer, 'magento.res.partner.category')
            importer.run(group_id)

    def _before_import(self):
        rules = self.get_connector_unit_for_model(SaleImportRule)
        rules.check(self.magento_record)

    def _create_payment(self, binding_id):
        sess = self.session
        mag_sale = sess.browse(self.model._name, binding_id)
        if not mag_sale.payment_method_id.journal_id:
            return
        sale_obj = sess.pool['sale.order']
        amount = self.magento_record.get('payment', {}).get('amount_paid')
        if amount:
            amount = float(amount)  # magento gives a str
            cr, uid, context = sess.cr, sess.uid, sess.context
            sale_obj.automatic_payment(cr, uid, mag_sale.openerp_id.id,
                                       amount, context=context)

    def _link_parent_orders(self, binding_id):
        """ Link the magento.sale.order to its parent orders.

        When a Magento sales order is modified, it:
         - cancel the sales order
         - create a copy and link the canceled one as a parent

        So we create the link to the parent sales orders.
        Note that we have to walk through all the chain of parent sales orders
        in the case of multiple editions / cancellations.
        """
        parent_id = self.magento_record.get('relation_parent_real_id')
        if not parent_id:
            return
        all_parent_ids = []
        while parent_id:
            all_parent_ids.append(parent_id)
            parent_id = self.backend_adapter.get_parent(parent_id)
        current_bind_id = binding_id
        for parent_id in all_parent_ids:
            parent_bind_id = self.binder.to_openerp(parent_id)
            if not parent_bind_id:
                # may happen if several sales orders have been
                # edited / canceled but not all have been imported
                continue
            # link to the nearest parent
            self.session.write(self.model._name,
                               current_bind_id,
                               {'magento_parent_id': parent_bind_id})
            parent_canceled = self.session.read(self.model._name,
                                                parent_bind_id,
                                                ['canceled_in_backend']
                                                )['canceled_in_backend']
            if not parent_canceled:
                self.session.write(self.model._name,
                                   parent_bind_id,
                                   {'canceled_in_backend': True})
            current_bind_id = parent_bind_id

    def _after_import(self, binding_id):
        self._link_parent_orders(binding_id)
        self._create_payment(binding_id)
        binding = self.session.browse(self.model._name, binding_id)
        if binding.magento_parent_id:
            move_comment = self.environment.get_connector_unit(
                SaleOrderMoveComment)
            move_comment.move(binding)

    def _get_storeview(self, record):
        """ Return the tax inclusion setting for the appropriate storeview """
        storeview_binder = self.get_binder_for_model('magento.storeview')
        # we find storeview_id in store_id!
        # (http://www.magentocommerce.com/bug-tracking/issue?issue=15886)
        storeview_id = storeview_binder.to_openerp(record['store_id'])
        storeview = self.session.browse('magento.storeview', storeview_id)
        return storeview

    def _get_magento_data(self):
        """ Return the raw Magento data for ``self.magento_id`` """
        record = super(SaleOrderImport, self)._get_magento_data()
        # sometimes we don't have website_id...
        # we fix the record!
        if not record.get('website_id'):
            storeview = self._get_storeview(record)
            # deduce it from the storeview
            record['website_id'] = storeview.store_id.website_id.magento_id
        # sometimes we need to clean magento items (ex : configurable
        # product in a sale)
        record = self._clean_magento_items(record)
        return record

    def _import_addresses(self):
        record = self.magento_record
        sess = self.session

        # Magento allows to create a sale order not registered as a user
        is_guest_order = bool(int(record.get('customer_is_guest', 0) or 0))

        # For a guest order or when magento does not provide customer_id
        # on a non-guest order (it happens, Magento inconsistencies are
        # common)
        if (is_guest_order or not record.get('customer_id')):
            website_binder = self.get_binder_for_model('magento.website')
            oe_website_id = website_binder.to_openerp(record['website_id'])

            # search an existing partner with the same email
            partner_ids = sess.search(
                'magento.res.partner',
                [('emailid', '=', record['customer_email']),
                 ('website_id', '=', oe_website_id)])

            # if we have found one, we "fix" the record with the magento
            # customer id
            if partner_ids:
                partner = sess.read('magento.res.partner',
                                    partner_ids[0],
                                    ['magento_id'])
                # If there are multiple orders with "customer_id is
                # null" and "customer_is_guest = 0" which share the same
                # customer_email, then we may get a magento_id that is a
                # marker 'guestorder:...' for a guest order (which is
                # set below).  This causes a problem with
                # "importer.run..." below where the id is cast to int.
                if str(partner['magento_id']).startswith('guestorder:'):
                    is_guest_order = True
                else:
                    record['customer_id'] = partner['magento_id']

            # no partner matching, it means that we have to consider it
            # as a guest order
            else:
                is_guest_order = True

        partner_binder = self.get_binder_for_model('magento.res.partner')
        if is_guest_order:
            # ensure that the flag is correct in the record
            record['customer_is_guest'] = True
            guest_customer_id = 'guestorder:%s' % record['increment_id']
            # "fix" the record with a on-purpose built ID so we can found it
            # from the mapper
            record['customer_id'] = guest_customer_id

            address = record['billing_address']

            customer_group = record.get('customer_group_id')
            if customer_group:
                self._import_customer_group(customer_group)

            customer_record = {
                'firstname': address['firstname'],
                'middlename': address['middlename'],
                'lastname': address['lastname'],
                'prefix': address.get('prefix'),
                'suffix': address.get('suffix'),
                'email': record.get('customer_email'),
                'taxvat': record.get('customer_taxvat'),
                'group_id': customer_group,
                'gender': record.get('customer_gender'),
                'store_id': record['store_id'],
                'created_at': record['created_at'],
                'updated_at': False,
                'created_in': False,
                'dob': record.get('customer_dob'),
                'website_id': record.get('website_id'),
            }
            mapper = self.get_connector_unit_for_model(PartnerImportMapper,
                                                       'magento.res.partner')
            map_record = mapper.map_record(customer_record)
            map_record.update(guest_customer=True)
            partner_bind_id = sess.create('magento.res.partner',
                                          map_record.values(for_create=True))
            partner_binder.bind(guest_customer_id,
                                partner_bind_id)
        else:

            # we always update the customer when importing an order
            importer = self.get_connector_unit_for_model(
                MagentoImportSynchronizer, 'magento.res.partner')
            importer.run(record['customer_id'])
            partner_bind_id = partner_binder.to_openerp(record['customer_id'])

        partner_id = sess.read(
            'magento.res.partner',
            partner_bind_id, ['openerp_id'])['openerp_id'][0]

        # Import of addresses. We just can't rely on the
        # ``customer_address_id`` field given by Magento, because it is
        # sometimes empty and sometimes wrong.

        # The addresses of the sale order are imported as active=false
        # so they are linked with the sale order but they are not displayed
        # in the customer form and the searches.

        # We import the addresses of the sale order as Active = False
        # so they will be available in the documents generated as the
        # sale order or the picking, but they won't be available on
        # the partner form or the searches. Too many adresses would
        # be displayed.
        # They are never synchronized.

        # For the orders which are from guests, we let the addresses
        # as active because they don't have an address book.
        addresses_defaults = {'parent_id': partner_id,
                              'magento_partner_id': partner_bind_id,
                              'email': record.get('customer_email', False),
                              'active': is_guest_order,
                              'is_magento_order_address': True}

        addr_mapper = self.get_connector_unit_for_model(ImportMapper,
                                                        'magento.address')

        def create_address(address_record):
            map_record = addr_mapper.map_record(address_record)
            map_record.update(addresses_defaults)
            address_bind_id = sess.create('magento.address',
                                          map_record.values(for_create=True))
            return sess.read('magento.address',
                             address_bind_id,
                             ['openerp_id'])['openerp_id'][0]

        billing_id = create_address(record['billing_address'])

        shipping_id = None
        if record['shipping_address']:
            shipping_id = create_address(record['shipping_address'])

        self.partner_id = partner_id
        self.partner_invoice_id = billing_id
        self.partner_shipping_id = shipping_id or billing_id

    def _check_special_fields(self):
        assert self.partner_id, (
            "self.partner_id should have been defined "
            "in SaleOrderImport._import_addresses")
        assert self.partner_invoice_id, (
            "self.partner_id should have been "
            "defined in SaleOrderImport._import_addresses")
        assert self.partner_shipping_id, (
            "self.partner_id should have been defined "
            "in SaleOrderImport._import_addresses")

    def _create_data(self, map_record, **kwargs):
        storeview = self._get_storeview(map_record.source)
        self._check_special_fields()
        return super(SaleOrderImport, self)._create_data(
            map_record,
            tax_include=storeview.catalog_price_tax_included,
            partner_id=self.partner_id,
            partner_invoice_id=self.partner_invoice_id,
            partner_shipping_id=self.partner_shipping_id,
            storeview=storeview,
            **kwargs)

    def _update_data(self, map_record, **kwargs):
        storeview = self._get_storeview(map_record.source)
        self._check_special_fields()
        return super(SaleOrderImport, self)._update_data(
            map_record,
            tax_include=storeview.catalog_price_tax_included,
            partner_id=self.partner_id,
            partner_invoice_id=self.partner_invoice_id,
            partner_shipping_id=self.partner_shipping_id,
            storeview=storeview,
            **kwargs)

    def _import_dependencies(self):
        record = self.magento_record

        self._import_addresses()

        for line in record.get('items', []):
            _logger.debug('line: %s', line)
            if 'product_id' in line:
                self._import_dependency(line['product_id'],
                                        'magento.product.product')


@magento
class SaleOrderCommentImportMapper(ImportMapper):
    """ Mapper for importing comments of sales orders.

    Does nothing in the base addons.
    """
    _model_name = 'magento.sale.order'


@magento
class SaleOrderImportMapper(ImportMapper):
    _model_name = 'magento.sale.order'

    direct = [('increment_id', 'magento_id'),
              ('order_id', 'magento_order_id'),
              ('grand_total', 'total_amount'),
              ('tax_amount', 'total_amount_tax'),
              ('created_at', 'date_order'),
              ('store_id', 'storeview_id'),
              ]

    children = [('items', 'magento_order_line_ids', 'magento.sale.order.line'),
                ]

    def _add_shipping_line(self, map_record, values):
        record = map_record.source
        amount_incl = float(record.get('base_shipping_incl_tax') or 0.0)
        amount_excl = float(record.get('shipping_amount') or 0.0)
        if not (amount_incl or amount_excl):
            return values
        line_builder = self.get_connector_unit_for_model(
            MagentoShippingLineBuilder)
        if self.options.tax_include:
            discount = float(record.get('shipping_discount_amount') or 0.0)
            line_builder.price_unit = (amount_incl - discount)
        else:
            line_builder.price_unit = amount_excl

        if values.get('carrier_id'):
            carrier = self.session.browse('delivery.carrier',
                                          values['carrier_id'])
            line_builder.product_id = carrier.product_id

        line = (0, 0, line_builder.get_line())
        values['order_line'].append(line)
        return values

    def _add_cash_on_delivery_line(self, map_record, values):
        record = map_record.source
        amount_excl = float(record.get('cod_fee') or 0.0)
        amount_incl = float(record.get('cod_tax_amount') or 0.0)
        if not (amount_excl or amount_incl):
            return values
        line_builder = self.get_connector_unit_for_model(
            MagentoCashOnDeliveryLineBuilder)
        tax_include = self.options.tax_include
        line_builder.price_unit = amount_incl if tax_include else amount_excl
        line = (0, 0, line_builder.get_line())
        values['order_line'].append(line)
        return values

    def _add_gift_certificate_line(self, map_record, values):
        record = map_record.source
        if 'gift_cert_amount' not in record:
            return values
        amount = float(record['gift_cert_amount'])
        line_builder = self.get_connector_unit_for_model(
            MagentoGiftOrderLineBuilder)
        line_builder.price_unit = amount
        if 'gift_cert_code' in record:
            line_builder.code = record['gift_cert_code']
        line = (0, 0, line_builder.get_line())
        values['order_line'].append(line)
        return values

    def finalize(self, map_record, values):
        values.setdefault('order_line', [])
        values = self._add_shipping_line(map_record, values)
        values = self._add_cash_on_delivery_line(map_record, values)
        values = self._add_gift_certificate_line(map_record, values)
        values.update({
            'partner_id': self.options.partner_id,
            'partner_invoice_id': self.options.partner_invoice_id,
            'partner_shipping_id': self.options.partner_shipping_id,
        })
        onchange = self.get_connector_unit_for_model(SaleOrderOnChange)
        return onchange.play(values, values['magento_order_line_ids'])

    @mapping
    def name(self, record):
        name = record['increment_id']
        prefix = self.backend_record.sale_prefix
        if prefix:
            name = prefix + name
        return {'name': name}

    @mapping
    def store_id(self, record):
        shop_id = self.options.storeview.store_id.openerp_id.id
        return {'shop_id': shop_id}

    @mapping
    def customer_id(self, record):
        binder = self.get_binder_for_model('magento.res.partner')
        partner_id = binder.to_openerp(record['customer_id'], unwrap=True)
        assert partner_id is not None, (
            "customer_id %s should have been imported in "
            "SaleOrderImport._import_dependencies" % record['customer_id'])
        return {'partner_id': partner_id}

    @mapping
    def payment(self, record):
        record_method = record['payment']['method']
        method_ids = self.session.search('payment.method',
                                         [['name', '=', record_method]])
        assert method_ids, ("method %s should exist because the import fails "
                            "in SaleOrderImport._before_import when it is "
                            " missing" % record['payment']['method'])
        method_id = method_ids[0]
        return {'payment_method_id': method_id}

    @mapping
    def shipping_method(self, record):
        session = self.session
        ifield = record.get('shipping_method')
        if not ifield:
            return

        carrier_ids = session.search('delivery.carrier',
                                     [('magento_code', '=', ifield)])
        if carrier_ids:
            result = {'carrier_id': carrier_ids[0]}
        else:
            fake_partner_id = session.search('res.partner', [])[0]
            model_data_obj = session.pool['ir.model.data']
            model, product_id = model_data_obj.get_object_reference(
                session.cr, session.uid,
                'connector_ecommerce',
                'product_product_shipping')
            carrier_id = session.create('delivery.carrier',
                                        {'partner_id': fake_partner_id,
                                         'product_id': product_id,
                                         'name': ifield,
                                         'magento_code': ifield,
                                         })
            result = {'carrier_id': carrier_id}
        return result

    # partner_id, partner_invoice_id, partner_shipping_id
    # are done in the importer

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}

    @mapping
    def user_id(self, record):
        """ Do not assign to a Salesperson otherwise sales orders are hidden
        for the salespersons (access rules)"""
        return {'user_id': False}

    @mapping
    def sale_order_comment(self, record):
        comment_mapper = self.environment.get_connector_unit(
            SaleOrderCommentImportMapper)
        map_record = comment_mapper.map_record(record)
        return map_record.values()


@magento
class MagentoSaleOrderOnChange(SaleOrderOnChange):
    _model_name = 'magento.sale.order'


@magento
class SaleOrderLineImportMapper(ImportMapper):
    _model_name = 'magento.sale.order.line'

    direct = [('qty_ordered', 'product_uom_qty'),
              ('qty_ordered', 'product_uos_qty'),
              ('name', 'name'),
              ('item_id', 'magento_id'),
              ]

    @mapping
    def discount_amount(self, record):
        discount_value = float(record.get('discount_amount') or 0)
        if self.options.tax_include:
            row_total = float(record.get('row_total_incl_tax') or 0)
        else:
            row_total = float(record.get('row_total') or 0)
        discount = 0
        if discount_value > 0 and row_total > 0:
            discount = 100 * discount_value / row_total
        result = {'discount': discount}
        return result

    @mapping
    def product_id(self, record):
        binder = self.get_binder_for_model('magento.product.product')
        product_id = binder.to_openerp(record['product_id'], unwrap=True)
        assert product_id is not None, (
            "product_id %s should have been imported in "
            "SaleOrderImport._import_dependencies" % record['product_id'])
        return {'product_id': product_id}

    @mapping
    def product_options(self, record):
        result = {}
        ifield = record['product_options']
        if ifield:
            import re
            options_label = []
            clean = re.sub(r'\w:\w:|\w:\w+;', '', ifield)
            for each in clean.split('{'):
                if each.startswith('"label"'):
                    split_info = each.split(';')
                    options_label.append('%s: %s [%s]' % (split_info[1],
                                                          split_info[3],
                                                          record['sku']))
            notes = "".join(options_label).replace('""', '\n').replace('"', '')
            result = {'notes': notes}
        return result

    @mapping
    def price(self, record):
        result = {}
        base_row_total = float(record['base_row_total'] or 0.)
        base_row_total_incl_tax = float(record['base_row_total_incl_tax'] or
                                        0.)
        qty_ordered = float(record['qty_ordered'])
        if self.options.tax_include:
            result['price_unit'] = base_row_total_incl_tax / qty_ordered
        else:
            result['price_unit'] = base_row_total / qty_ordered
        return result


@magento
class MagentoShippingLineBuilder(ShippingLineBuilder):
    _model_name = 'magento.sale.order'


@magento
class MagentoCashOnDeliveryLineBuilder(CashOnDeliveryLineBuilder):
    _model_name = 'magento.sale.order'


@magento
class MagentoGiftOrderLineBuilder(GiftOrderLineBuilder):
    _model_name = 'magento.sale.order'


@job
def sale_order_import_batch(session, model_name, backend_id, filters=None):
    """ Prepare a batch import of records from Magento """
    if filters is None:
        filters = {}
    assert 'magento_storeview_id' in filters, ('Missing information about '
                                               'Magento Storeview')
    env = get_environment(session, model_name, backend_id)
    importer = env.get_connector_unit(SaleOrderBatchImport)
    importer.run(filters)


@magento
class SaleCommentAdapter(GenericAdapter):
    _model_name = 'magento.sale.comment'

    def create(self, order_increment, status, comment=None, notify=False):
        return self._call('sales_order.addComment',
                          [order_increment, status, comment, notify])
