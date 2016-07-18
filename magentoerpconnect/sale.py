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
from openerp import models, fields, api, _
from openerp.addons.connector.connector import ConnectorUnit
from openerp.addons.connector.session import ConnectorSession
from openerp.addons.connector.exception import (NothingToDoJob,
                                                FailedJobError,
                                                IDMissingInBackend)
from openerp.addons.connector.queue.job import job
from openerp.addons.connector.unit.synchronizer import Exporter
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
from .unit.import_synchronizer import (DelayedBatchImporter,
                                       MagentoImporter,
                                       )
from .unit.mapper import normalize_datetime
from .exception import OrderImportRuleRetry
from .backend import magento
from .connector import get_environment
from .partner import PartnerImportMapper

_logger = logging.getLogger(__name__)

ORDER_STATUS_MAPPING = {  # used in magentoerpconnect_order_comment
    'draft': 'pending',
    'manual': 'processing',
    'progress': 'processing',
    'shipping_except': 'processing',
    'invoice_except': 'processing',
    'done': 'complete',
    'cancel': 'canceled',
    'waiting_date': 'holded'
}


class MagentoSaleOrder(models.Model):
    _name = 'magento.sale.order'
    _inherit = 'magento.binding'
    _description = 'Magento Sale Order'
    _inherits = {'sale.order': 'openerp_id'}

    openerp_id = fields.Many2one(comodel_name='sale.order',
                                 string='Sale Order',
                                 required=True,
                                 ondelete='cascade')
    magento_order_line_ids = fields.One2many(
        comodel_name='magento.sale.order.line',
        inverse_name='magento_order_id',
        string='Magento Order Lines'
    )
    total_amount = fields.Float(
        string='Total amount',
        digits_compute=dp.get_precision('Account')
    )
    total_amount_tax = fields.Float(
        string='Total amount w. tax',
        digits_compute=dp.get_precision('Account')
    )
    magento_order_id = fields.Integer(string='Magento Order ID',
                                      help="'order_id' field in Magento")
    # when a sale order is modified, Magento creates a new one, cancels
    # the parent order and link the new one to the canceled parent
    magento_parent_id = fields.Many2one(comodel_name='magento.sale.order',
                                        string='Parent Magento Order')
    storeview_id = fields.Many2one(comodel_name='magento.storeview',
                                   string='Magento Storeview')
    store_id = fields.Many2one(related='storeview_id.store_id',
                               string='Storeview',
                               readonly=True)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    magento_bind_ids = fields.One2many(
        comodel_name='magento.sale.order',
        inverse_name='openerp_id',
        string="Magento Bindings",
    )

    @api.one
    @api.depends('magento_bind_ids', 'magento_bind_ids.magento_parent_id')
    def get_parent_id(self):
        """ Return the parent order.

        For Magento sales orders, the magento parent order is stored
        in the binding, get it from there.
        """
        super(SaleOrder, self).get_parent_id()
        for order in self:
            if not order.magento_bind_ids:
                continue
            # assume we only have 1 SO in OpenERP for 1 SO in Magento
            magento_order = order.magento_bind_ids[0]
            if magento_order.magento_parent_id:
                self.parent_id = magento_order.magento_parent_id.openerp_id

    @api.multi
    def write(self, vals):
        # cancel sales order on Magento (do not export the other
        # state changes, Magento handles them itself)
        if vals.get('state') == 'cancel':
            session = ConnectorSession(self.env.cr, self.env.uid,
                                       context=self.env.context)
            for order in self:
                old_state = order.state
                if old_state == 'cancel':
                    continue  # skip if already canceled
                for binding in order.magento_bind_ids:
                    export_state_change.delay(
                        session,
                        'magento.sale.order',
                        binding.id,
                        # so if the state changes afterwards,
                        # it won't be exported
                        allowed_states=['cancel'],
                        description="Cancel sales order %s" %
                                    binding.magento_id)
        return super(SaleOrder, self).write(vals)

    @api.multi
    def copy_quotation(self):
        self_copy = self.with_context(__copy_from_quotation=True)
        result = super(SaleOrder, self_copy).copy_quotation()
        # link binding of the canceled order to the new order, so the
        # operations done on the new order will be sync'ed with Magento
        new_id = result['res_id']
        binding_model = self.env['magento.sale.order']
        bindings = binding_model.search([('openerp_id', '=', self.id)])
        bindings.write({'openerp_id': new_id})
        session = ConnectorSession(self.env.cr, self.env.uid,
                                   context=self.env.context)
        for binding in bindings:
            # the sales' status on Magento is likely 'canceled'
            # so we will export the new status (pending, processing, ...)
            export_state_change.delay(
                session,
                'magento.sale.order',
                binding.id,
                description="Reopen sales order %s" % binding.magento_id)
        return result


class MagentoSaleOrderLine(models.Model):
    _name = 'magento.sale.order.line'
    _inherit = 'magento.binding'
    _description = 'Magento Sale Order Line'
    _inherits = {'sale.order.line': 'openerp_id'}

    magento_order_id = fields.Many2one(comodel_name='magento.sale.order',
                                       string='Magento Sale Order',
                                       required=True,
                                       ondelete='cascade',
                                       select=True)
    openerp_id = fields.Many2one(comodel_name='sale.order.line',
                                 string='Sale Order Line',
                                 required=True,
                                 ondelete='cascade')
    backend_id = fields.Many2one(
        related='magento_order_id.backend_id',
        string='Magento Backend',
        readonly=True,
        store=True,
        # override 'magento.binding', can't be INSERTed if True:
        required=False,
    )
    tax_rate = fields.Float(string='Tax Rate',
                            digits_compute=dp.get_precision('Account'))
    notes = fields.Char()

    @api.model
    def create(self, vals):
        magento_order_id = vals['magento_order_id']
        binding = self.env['magento.sale.order'].browse(magento_order_id)
        vals['order_id'] = binding.openerp_id.id
        binding = super(MagentoSaleOrderLine, self).create(vals)
        # FIXME triggers function field
        # The amounts (amount_total, ...) computed fields on 'sale.order' are
        # not triggered when magento.sale.order.line are created.
        # It might be a v8 regression, because they were triggered in
        # v7. Before getting a better correction, force the computation
        # by writing again on the line.
        line = binding.openerp_id
        line.write({'price_unit': line.price_unit})
        return binding


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    magento_bind_ids = fields.One2many(
        comodel_name='magento.sale.order.line',
        inverse_name='openerp_id',
        string="Magento Bindings",
    )

    @api.model
    def create(self, vals):
        old_line_id = None
        if self.env.context.get('__copy_from_quotation'):
            # when we are copying a sale.order from a canceled one,
            # the id of the copied line is inserted in the vals
            # in `copy_data`.
            old_line_id = vals.pop('__copy_from_line_id', None)
        new_line = super(SaleOrderLine, self).create(vals)
        if old_line_id:
            # link binding of the canceled order lines to the new order
            # lines, happens when we are using the 'New Copy of
            # Quotation' button on a canceled sales order
            binding_model = self.env['magento.sale.order.line']
            bindings = binding_model.search([('openerp_id', '=', old_line_id)])
            if bindings:
                bindings.write({'openerp_id': new_line.id})
        return new_line

    # XXX we can't use the new API on copy_data or we get an error:
    # 'setdefault' not supported on frozendict
    def copy_data(self, cr, uid, id, default=None, context=None):
        if context is None:
            context = {}

        data = super(SaleOrderLine, self).copy_data(cr, uid, id,
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

    def add_comment(self, id, status, comment=None, notify=False):
        return self._call('%s.addComment' % self._magento_model,
                          [id, status, comment, notify])


@magento
class SaleOrderBatchImport(DelayedBatchImporter):
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
        payment_method = record['payment']['method']
        method = self.env['payment.method'].search(
            [('name', '=', payment_method)],
            limit=1,
        )
        if not method:
            raise FailedJobError(
                "The configuration is missing for the Payment Method '%s'.\n\n"
                "Resolution:\n"
                "- Go to "
                "'Sales > Configuration > Sales > Customer Payment Method\n"
                "- Create a new Payment Method with name '%s'\n"
                "-Eventually  link the Payment Method to an existing Workflow "
                "Process or create a new one." % (payment_method,
                                                  payment_method))
        self._rule_global(record, method)
        self._rules[method.import_rule](self, record, method)


@magento
class SaleOrderMoveComment(ConnectorUnit):
    _model_name = ['magento.sale.order']

    def move(self, binding):
        pass


@magento
class SaleOrderImportMapper(ImportMapper):
    _model_name = 'magento.sale.order'

    direct = [('increment_id', 'magento_id'),
              ('order_id', 'magento_order_id'),
              ('grand_total', 'total_amount'),
              ('tax_amount', 'total_amount_tax'),
              (normalize_datetime('created_at'), 'date_order'),
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
        line_builder = self.unit_for(MagentoShippingLineBuilder)
        if self.options.tax_include:
            discount = float(record.get('shipping_discount_amount') or 0.0)
            line_builder.price_unit = (amount_incl - discount)
        else:
            line_builder.price_unit = amount_excl

        if values.get('carrier_id'):
            carrier = self.env['delivery.carrier'].browse(values['carrier_id'])
            line_builder.product = carrier.product_id

        line = (0, 0, line_builder.get_line())
        values['order_line'].append(line)
        return values

    def _add_cash_on_delivery_line(self, map_record, values):
        record = map_record.source
        amount_excl = float(record.get('cod_fee') or 0.0)
        amount_incl = float(record.get('cod_tax_amount') or 0.0)
        if not (amount_excl or amount_incl):
            return values
        line_builder = self.unit_for(MagentoCashOnDeliveryLineBuilder)
        tax_include = self.options.tax_include
        line_builder.price_unit = amount_incl if tax_include else amount_excl
        line = (0, 0, line_builder.get_line())
        values['order_line'].append(line)
        return values

    def _add_gift_certificate_line(self, map_record, values):
        record = map_record.source
        if 'gift_cert_amount' not in record:
            return values
        # if gift_cert_amount is zero
        if not record.get('gift_cert_amount'):
            return values
        amount = float(record['gift_cert_amount'])
        line_builder = self.unit_for(MagentoGiftOrderLineBuilder)
        line_builder.price_unit = amount
        if 'gift_cert_code' in record:
            line_builder.gift_code = record['gift_cert_code']
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
        onchange = self.unit_for(SaleOrderOnChange)
        return onchange.play(values, values['magento_order_line_ids'])

    @mapping
    def name(self, record):
        name = record['increment_id']
        prefix = self.backend_record.sale_prefix
        if prefix:
            name = prefix + name
        return {'name': name}

    @mapping
    def customer_id(self, record):
        binder = self.binder_for('magento.res.partner')
        partner_id = binder.to_openerp(record['customer_id'], unwrap=True)
        assert partner_id is not None, (
            "customer_id %s should have been imported in "
            "SaleOrderImporter._import_dependencies" % record['customer_id'])
        return {'partner_id': partner_id}

    @mapping
    def payment(self, record):
        record_method = record['payment']['method']
        method = self.env['payment.method'].search(
            [['name', '=', record_method]],
            limit=1,
        )
        assert method, ("method %s should exist because the import fails "
                        "in SaleOrderImporter._before_import when it is "
                        " missing" % record['payment']['method'])
        return {'payment_method_id': method.id}

    @mapping
    def shipping_method(self, record):
        ifield = record.get('shipping_method')
        if not ifield:
            return

        carrier = self.env['delivery.carrier'].search(
            [('magento_code', '=', ifield)],
            limit=1,
        )
        if carrier:
            result = {'carrier_id': carrier.id}
        else:
            fake_partner = self.env['res.partner'].search([], limit=1)
            product = self.env.ref(
                'connector_ecommerce.product_product_shipping')
            carrier = self.env['delivery.carrier'].create({
                'partner_id': fake_partner.id,
                'product_id': product.id,
                'name': ifield,
                'magento_code': ifield})
            result = {'carrier_id': carrier.id}
        return result

    @mapping
    def sales_team(self, record):
        team = self.options.storeview.section_id
        if team:
            return {'section_id': team.id}

    @mapping
    def project_id(self, record):
        project_id = self.options.storeview.account_analytic_id
        if project_id:
            return {'project_id': project_id.id}

    @mapping
    def fiscal_position(self, record):
        fiscal_position = self.options.storeview.fiscal_position_id
        if fiscal_position:
            return {'fiscal_position': fiscal_position.id}

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
        comment_mapper = self.unit_for(SaleOrderCommentImportMapper)
        map_record = comment_mapper.map_record(record)
        return map_record.values(**self.options)

    @mapping
    def pricelist_id(self, record):
        pricelist_mapper = self.unit_for(PricelistSaleOrderImportMapper)
        return pricelist_mapper.map_record(record).values(**self.options)


@magento
class SaleOrderImporter(MagentoImporter):
    _model_name = ['magento.sale.order']

    _base_mapper = SaleOrderImportMapper

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
        binder = self.binder_for('magento.res.partner.category')
        if binder.to_openerp(group_id) is None:
            importer = self.unit_for(MagentoImporter,
                                     model='magento.res.partner.category')
            importer.run(group_id)

    def _before_import(self):
        rules = self.unit_for(SaleImportRule)
        rules.check(self.magento_record)

    def _create_payment(self, binding):
        if not binding.payment_method_id.journal_id:
            return
        amount = self.magento_record.get('payment', {}).get('amount_paid')
        if amount:
            amount = float(amount)  # magento gives a str
            binding.openerp_id.automatic_payment(amount)

    def _link_parent_orders(self, binding):
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
        current_binding = binding
        for parent_id in all_parent_ids:
            parent_binding = self.binder.to_openerp(parent_id, browse=True)
            if not parent_binding:
                # may happen if several sales orders have been
                # edited / canceled but not all have been imported
                continue
            # link to the nearest parent
            current_binding.write({'magento_parent_id': parent_binding.id})
            parent_canceled = parent_binding.canceled_in_backend
            if not parent_canceled:
                parent_binding.write({'canceled_in_backend': True})
            current_binding = parent_binding

    def _after_import(self, binding):
        self._link_parent_orders(binding)
        self._create_payment(binding)
        if binding.magento_parent_id:
            move_comment = self.unit_for(SaleOrderMoveComment)
            move_comment.move(binding)

    def _get_storeview(self, record):
        """ Return the tax inclusion setting for the appropriate storeview """
        storeview_binder = self.binder_for('magento.storeview')
        # we find storeview_id in store_id!
        # (http://www.magentocommerce.com/bug-tracking/issue?issue=15886)
        return storeview_binder.to_openerp(record['store_id'], browse=True)

    def _get_magento_data(self):
        """ Return the raw Magento data for ``self.magento_id`` """
        record = super(SaleOrderImporter, self)._get_magento_data()
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

        # Magento allows to create a sale order not registered as a user
        is_guest_order = bool(int(record.get('customer_is_guest', 0) or 0))

        # For a guest order or when magento does not provide customer_id
        # on a non-guest order (it happens, Magento inconsistencies are
        # common)
        if (is_guest_order or not record.get('customer_id')):
            website_binder = self.binder_for('magento.website')
            oe_website_id = website_binder.to_openerp(record['website_id'])

            # search an existing partner with the same email
            partner = self.env['magento.res.partner'].search(
                [('emailid', '=', record['customer_email']),
                 ('website_id', '=', oe_website_id)],
                limit=1)

            # if we have found one, we "fix" the record with the magento
            # customer id
            if partner:
                magento = partner.magento_id
                # If there are multiple orders with "customer_id is
                # null" and "customer_is_guest = 0" which share the same
                # customer_email, then we may get a magento_id that is a
                # marker 'guestorder:...' for a guest order (which is
                # set below).  This causes a problem with
                # "importer.run..." below where the id is cast to int.
                if str(magento).startswith('guestorder:'):
                    is_guest_order = True
                else:
                    record['customer_id'] = magento

            # no partner matching, it means that we have to consider it
            # as a guest order
            else:
                is_guest_order = True

        partner_binder = self.binder_for('magento.res.partner')
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
                'created_at': normalize_datetime('created_at')(self,
                                                               record, ''),
                'updated_at': False,
                'created_in': False,
                'dob': record.get('customer_dob'),
                'website_id': record.get('website_id'),
            }
            mapper = self.unit_for(PartnerImportMapper,
                                   model='magento.res.partner')
            map_record = mapper.map_record(customer_record)
            map_record.update(guest_customer=True)
            partner_binding = self.env['magento.res.partner'].create(
                map_record.values(for_create=True))
            partner_binder.bind(guest_customer_id,
                                partner_binding)
        else:

            # we always update the customer when importing an order
            importer = self.unit_for(MagentoImporter,
                                     model='magento.res.partner')
            importer.run(record['customer_id'])
            partner_binding = partner_binder.to_openerp(record['customer_id'],
                                                        browse=True)

        partner = partner_binding.openerp_id

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
        addresses_defaults = {'parent_id': partner.id,
                              'magento_partner_id': partner_binding.id,
                              'email': record.get('customer_email', False),
                              'active': False,
                              'is_magento_order_address': True}

        addr_mapper = self.unit_for(ImportMapper, model='magento.address')

        def create_address(address_record):
            map_record = addr_mapper.map_record(address_record)
            map_record.update(addresses_defaults)
            address_bind = self.env['magento.address'].create(
                map_record.values(for_create=True,
                                  parent_partner=partner))
            return address_bind.openerp_id.id

        billing_id = create_address(record['billing_address'])

        shipping_id = None
        if record['shipping_address']:
            shipping_id = create_address(record['shipping_address'])

        self.partner_id = partner.id
        self.partner_invoice_id = billing_id
        self.partner_shipping_id = shipping_id or billing_id

    def _check_special_fields(self):
        assert self.partner_id, (
            "self.partner_id should have been defined "
            "in SaleOrderImporter._import_addresses")
        assert self.partner_invoice_id, (
            "self.partner_id should have been "
            "defined in SaleOrderImporter._import_addresses")
        assert self.partner_shipping_id, (
            "self.partner_id should have been defined "
            "in SaleOrderImporter._import_addresses")

    def _create_data(self, map_record, **kwargs):
        storeview = self._get_storeview(map_record.source)
        self._check_special_fields()
        return super(SaleOrderImporter, self)._create_data(
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
        return super(SaleOrderImporter, self)._update_data(
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


SaleOrderImport = SaleOrderImporter  # deprecated


@magento
class PricelistSaleOrderImportMapper(ImportMapper):
    """ Mapper for importing the sales order pricelist

    Does nothing by default. Replaced in magentoerpconnect_pricing.
    """
    _model_name = 'magento.sale.order'


@magento
class SaleOrderCommentImportMapper(ImportMapper):
    """ Mapper for importing comments of sales orders.

    Does nothing in the base addons.
    """
    _model_name = 'magento.sale.order'


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
        binder = self.binder_for('magento.product.product')
        product_id = binder.to_openerp(record['product_id'], unwrap=True)
        assert product_id is not None, (
            "product_id %s should have been imported in "
            "SaleOrderImporter._import_dependencies" % record['product_id'])
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


@job(default_channel='root.magento')
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
class StateExporter(Exporter):
    _model_name = 'magento.sale.order'

    def run(self, binding_id, allowed_states=None, comment=None, notify=False):
        """ Change the status of the sales order on Magento.

        It adds a comment on Magento with a status.
        Sales orders on Magento have a state and a status.
        The state is related to the sale workflow, and the status can be
        modified liberaly.  We change only the status because Magento
        handle the state itself.

        When a sales order is modified, if we used the ``sales_order.cancel``
        API method, we would not be able to revert the cancellation.  When
        we send ``cancel`` as a status change with a new comment, we are still
        able to change the status again and to create shipments and invoices
        because the state is still ``new`` or ``processing``.

        :param binding_id: ID of the binding record of the sales order
        :param allowed_states: list of OpenERP states that are allowed
                               for export. If empty, it will export any
                               state.
        :param comment: Comment to display on Magento for the state change
        :param notify: When True, Magento will send an email with the
                       comment
        """
        binding = self.model.browse(binding_id)
        state = binding.state
        if allowed_states and state not in allowed_states:
            return _('State %s is not exported.') % state
        magento_id = self.binder.to_backend(binding.id)
        if not magento_id:
            return _('Sale is not linked with a Magento sales order')
        magento_state = ORDER_STATUS_MAPPING[state]
        record = self.backend_adapter.read(magento_id)
        if record['status'] == magento_state:
            return _('Magento sales order is already '
                     'in state %s') % magento_state
        self.backend_adapter.add_comment(magento_id, magento_state,
                                         comment=comment,
                                         notify=notify)
        self.binder.bind(magento_id, binding_id)


@job(default_channel='root.magento')
def export_state_change(session, model_name, binding_id, allowed_states=None,
                        comment=None, notify=None):
    """ Change state of a sales order on Magento """
    binding = session.env[model_name].browse(binding_id)
    backend_id = binding.backend_id.id
    env = get_environment(session, model_name, backend_id)
    exporter = env.get_connector_unit(StateExporter)
    return exporter.run(binding_id, allowed_states=allowed_states,
                        comment=comment, notify=notify)
