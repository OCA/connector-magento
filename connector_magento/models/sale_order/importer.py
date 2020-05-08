# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging

from re import search as re_search
from datetime import datetime, timedelta

from odoo import _
from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping
from odoo.addons.queue_job.exception import NothingToDoJob, FailedJobError
from ...components.mapper import normalize_datetime
from ...exception import OrderImportRuleRetry

_logger = logging.getLogger(__name__)


class SaleOrderBatchImporter(Component):
    _name = 'magento.sale.order.batch.importer'
    _inherit = 'magento.delayed.batch.importer'
    _apply_on = 'magento.sale.order'

    def _import_record(self, external_id, job_options=None, **kwargs):
        job_options = {
            'max_retries': 0,
            'priority': 5,
        }
        return super(SaleOrderBatchImporter, self)._import_record(
            external_id, job_options=job_options)

    def run(self, filters=None):
        """ Run the synchronization """
        if filters is None:
            filters = {}
        filters['state'] = {'neq': 'canceled'}
        from_date = filters.pop('from_date', None)
        to_date = filters.pop('to_date', None)
        magento_storeview_ids = [filters.pop('magento_storeview_id')]
        external_ids = self.backend_adapter.search(
            filters,
            from_date=from_date,
            to_date=to_date,
            magento_storeview_ids=magento_storeview_ids)
        _logger.info('search for magento saleorders %s returned %s',
                     filters, external_ids)
        for external_id in external_ids:
            self._import_record(external_id)


class SaleImportRule(Component):
    _name = 'magento.sale.import.rule'
    _inherit = 'base.magento.connector'
    _apply_on = 'magento.sale.order'
    _usage = 'sale.import.rule'

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
        method = self.env['account.payment.mode'].search(
            [('name', '=', payment_method)],
            limit=1,
        )
        if not method:
            raise FailedJobError(
                "The configuration is missing for the Payment Mode '%s'.\n\n"
                "Resolution:\n"
                "- Go to "
                "'Accounting > Configuration > Management > Payment Modes'\n"
                "- Create a new Payment Mode with name '%s'\n"
                "- Eventually link the Payment Mode to an existing Workflow "
                "Process or create a new one." % (payment_method,
                                                  payment_method))
        self._rule_global(record, method)
        self._rules[method.import_rule](self, record, method)


class SaleOrderImportMapper(Component):

    _name = 'magento.sale.order.mapper'
    _inherit = 'magento.import.mapper'
    _apply_on = 'magento.sale.order'

    direct = [('increment_id', 'external_id'),
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
        line_builder = self.component(usage='order.line.builder.shipping')
        # add even if the price is 0, otherwise odoo will add a shipping
        # line in the order when we ship the picking
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
        line_builder = self.component(usage='order.line.builder.cod')
        tax_include = self.options.tax_include
        line_builder.price_unit = amount_incl if tax_include else amount_excl
        line = (0, 0, line_builder.get_line())
        values['order_line'].append(line)
        return values

    def _add_gift_certificate_line(self, map_record, values):
        record = map_record.source
        # if gift_cert_amount is zero or doesn't exist
        if not record.get('gift_cert_amount'):
            return values
        amount = float(record['gift_cert_amount'])
        if amount == 0.0:
            return values
        line_builder = self.component(usage='order.line.builder.gift')
        line_builder.price_unit = amount
        if 'gift_cert_code' in record:
            line_builder.gift_code = record['gift_cert_code']
        line = (0, 0, line_builder.get_line())
        values['order_line'].append(line)
        return values

    def _add_gift_cards_line(self, map_record, values):
        record = map_record.source
        # if gift_cards_amount is zero or doesn't exist
        if not record.get('gift_cards_amount'):
            return values
        amount = float(record['gift_cards_amount'])
        if amount == 0.0:
            return values
        line_builder = self.component(usage='order.line.builder.gift')
        line_builder.price_unit = amount
        if 'gift_cards' in record:
            gift_code = ''
            gift_cards_serialized = record.get('gift_cards')
            codes = re_search(r's:1:"c";s:\d+:"(.*?)"', gift_cards_serialized)
            if codes:
                gift_code = ', '.join(codes.groups())
            line_builder.gift_code = gift_code
        line = (0, 0, line_builder.get_line())
        values['order_line'].append(line)
        return values

    def _add_store_credit_line(self, map_record, values):
        record = map_record.source
        if not record.get('customer_balance_amount'):
            return values
        amount = float(record['customer_balance_amount'])
        if amount == 0.0:
            return values
        line_builder = self.component(
            usage='order.line.builder.magento.store_credit')
        line_builder.price_unit = amount
        line = (0, 0, line_builder.get_line())
        values['order_line'].append(line)
        return values

    def _add_rewards_line(self, map_record, values):
        record = map_record.source
        if not record.get('reward_currency_amount'):
            return values
        amount = float(record['reward_currency_amount'])
        if amount == 0.0:
            return values
        line_builder = self.component(
            usage='order.line.builder.magento.rewards')
        line_builder.price_unit = amount
        line = (0, 0, line_builder.get_line())
        values['order_line'].append(line)
        return values

    def finalize(self, map_record, values):
        values.setdefault('order_line', [])
        values = self._add_shipping_line(map_record, values)
        values = self._add_cash_on_delivery_line(map_record, values)
        values = self._add_gift_certificate_line(map_record, values)
        values = self._add_gift_cards_line(map_record, values)
        values = self._add_store_credit_line(map_record, values)
        values = self._add_rewards_line(map_record, values)
        values.update({
            'partner_id': self.options.partner_id,
            'partner_invoice_id': self.options.partner_invoice_id,
            'partner_shipping_id': self.options.partner_shipping_id,
        })
        onchange = self.component(
            usage='ecommerce.onchange.manager.sale.order'
        )
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
        partner = binder.to_internal(record['customer_id'], unwrap=True)
        assert partner, (
            "customer_id %s should have been imported in "
            "SaleOrderImporter._import_dependencies" % record['customer_id'])
        return {'partner_id': partner.id}

    @mapping
    def payment(self, record):
        record_method = record['payment']['method']
        method = self.env['account.payment.mode'].search(
            [['name', '=', record_method]],
            limit=1,
        )
        assert method, ("method %s should exist because the import fails "
                        "in SaleOrderImporter._before_import when it is "
                        " missing" % record['payment']['method'])
        return {'payment_mode_id': method.id}

    @mapping
    def shipping_method(self, record):
        if self.collection.version == '2.0':
            shippings = record['extension_attributes']['shipping_assignments']
            ifield = shippings[0]['shipping'].get(
                'method') if shippings else None
        else:
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
            # FIXME: a mapper should not have any side effects
            product = self.env.ref(
                'connector_ecommerce.product_product_shipping')
            carrier = self.env['delivery.carrier'].create({
                'product_id': product.id,
                'name': ifield,
                'magento_code': ifield})
            result = {'carrier_id': carrier.id}
        return result

    @mapping
    def sales_team(self, record):
        team = self.options.storeview.team_id
        if team:
            return {'team_id': team.id}

    @mapping
    def analytic_account_id(self, record):
        analytic_account_id = self.options.storeview.account_analytic_id
        if analytic_account_id:
            return {'analytic_account_id': analytic_account_id.id}

    @mapping
    def fiscal_position(self, record):
        fiscal_position = self.options.storeview.fiscal_position_id
        if fiscal_position:
            return {'fiscal_position_id': fiscal_position.id}

    @mapping
    def warehouse_id(self, record):
        warehouse = self.options.storeview.warehouse_id
        if warehouse:
            return {'warehouse_id': warehouse.id}

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


class SaleOrderImporter(Component):
    _name = 'magento.sale.order.importer'
    _inherit = 'magento.importer'
    _apply_on = 'magento.sale.order'

    def _must_skip(self):
        """ Hook called right after we read the data from the backend.

        If the method returns a message giving a reason for the
        skipping, the import will be interrupted and the message
        recorded in the job (if the import is called directly by the
        job, not by dependencies).

        If it returns None, the import will continue normally.

        :returns: None | str | unicode
        """
        if self.binder.to_internal(self.external_id):
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
            # Experimental support for configurable products with multiple
            # subitems
            return [item] + child_items[1:]
        elif product_type == 'bundle':
            return child_items
        return top_item

    def _import_customer_group(self, group_id):
        self._import_dependency(group_id, 'magento.res.partner.category')

    def _before_import(self):
        rules = self.component(usage='sale.import.rule')
        rules.check(self.magento_record)

    def _link_parent_orders(self, binding):
        """ Link the magento.sale.order to its parent orders.

        When a Magento sales order is modified, it:
         - cancel the sales order
         - create a copy and link the canceled one as a parent

        So we create the link to the parent sales orders.
        Note that we have to walk through all the chain of parent sales orders
        in the case of multiple editions / cancellations.
        """
        if self.collection.version == '2.0':
            parent_id = self.magento_record.get('relation_parent_id')
        else:
            parent_id = self.magento_record.get('relation_parent_real_id')
        if not parent_id:
            return
        all_parent_ids = []
        while parent_id:
            all_parent_ids.append(parent_id)
            parent_id = self.backend_adapter.get_parent(parent_id)
        current_binding = binding
        for parent_id in all_parent_ids:
            parent_binding = self.binder.to_internal(parent_id)
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

    def _create(self, data):
        binding = super(SaleOrderImporter, self)._create(data)
        if binding.fiscal_position_id:
            binding.odoo_id._compute_tax_id()
        return binding

    def _after_import(self, binding):
        self._link_parent_orders(binding)

    def _get_storeview(self, record):
        """ Return the tax inclusion setting for the appropriate storeview """
        storeview_binder = self.binder_for('magento.storeview')
        # we find storeview_id in store_id!
        # (http://www.magentocommerce.com/bug-tracking/issue?issue=15886)
        return storeview_binder.to_internal(record['store_id'])

    def _get_magento_data(self):
        """ Return the raw Magento data for ``self.external_id`` """
        record = super(SaleOrderImporter, self)._get_magento_data()
        # sometimes we don't have website_id...
        # we fix the record!
        if not record.get('website_id'):
            storeview = self._get_storeview(record)
            # deduce it from the storeview
            record['website_id'] = storeview.store_id.website_id.external_id
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
            website_binding = website_binder.to_internal(record['website_id'])

            # search an existing partner with the same email
            partner = self.env['magento.res.partner'].search(
                [('emailid', '=', record['customer_email']),
                 ('website_id', '=', website_binding.id)],
                limit=1)

            # if we have found one, we "fix" the record with the magento
            # customer id
            if partner:
                magento = partner.external_id
                # If there are multiple orders with "customer_id is
                # null" and "customer_is_guest = 0" which share the same
                # customer_email, then we may get a external_id that is a
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
                'middlename': address.get('middlename'),
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
            mapper = self.component(usage='import.mapper',
                                    model_name='magento.res.partner')
            map_record = mapper.map_record(customer_record)
            map_record.update(guest_customer=True)
            partner_binding = self.env['magento.res.partner'].create(
                map_record.values(for_create=True))
            partner_binder.bind(guest_customer_id, partner_binding)
        else:

            # we always update the customer when importing an order
            importer = self.component(usage='record.importer',
                                      model_name='magento.res.partner')
            importer.run(record['customer_id'])
            partner_binding = partner_binder.to_internal(record['customer_id'])

        partner = partner_binding.odoo_id

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

        addr_mapper = self.component(usage='import.mapper',
                                     model_name='magento.address')

        def create_address(address_record):
            map_record = addr_mapper.map_record(address_record)
            map_record.update(addresses_defaults)
            address_bind = self.env['magento.address'].create(
                map_record.values(for_create=True,
                                  parent_partner=partner))
            return address_bind.odoo_id.id

        billing_id = create_address(record['billing_address'])

        shipping_id = None

        if self.collection.version == '1.7':
            shipping_address = record['shipping_address']
        else:
            # Magento 2.x allows for a different shipping address per line.
            # For now, we just take the first
            shippings = self.magento_record[
                'extension_attributes']['shipping_assignments']
            shipping_address = shippings[0]['shipping'].get(
                'address') if shippings else None
        if shipping_address:
            shipping_id = create_address(shipping_address)

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
                if self.collection.version == '1.7':
                    key = 'product_id'
                else:
                    key = 'sku'
                self._import_dependency(line[key],
                                        'magento.product.product')


class SaleOrderLineImportMapper(Component):

    _name = 'magento.sale.order.line.mapper'
    _inherit = 'magento.import.mapper'
    _apply_on = 'magento.sale.order.line'

    direct = [('qty_ordered', 'product_uom_qty'),
              ('qty_ordered', 'product_qty'),
              ('name', 'name'),
              ('item_id', 'external_id'),
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
        if self.collection.version == '1.7':
            key = 'product_id'
        else:
            key = 'sku'
        product = binder.to_internal(record[key], unwrap=True)
        assert product, (
            "product_id %s should have been imported in "
            "SaleOrderImporter._import_dependencies" % record[key])
        return {'product_id': product.id}

    @mapping
    def product_options(self, record):
        if self.collection.version == '2.0':
            # Product options look like this in Magento 2.0, so we'd have to
            # fetch the labels separately -> TODO
            # 'product_option': {
            #     'extension_attributes': {
            #         'configurable_item_options': [
            #             {'option_id': '152',
            #              'option_value': 5593},
            #             {'option_id': '93', 'option_value': 5477}
            #         ]
            #     }
            # }
            if record.get('product_option', {}).get(
                    'extension_attributes', {}).get(
                        'configurable_item_options'):
                _logger.debug(
                    'Magento order#%s contains a product with configurable '
                    'options but their import is not supported yet for '
                    'Magento2')
            return
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
        """ In Magento 2, base_row_total_incl_tax may not be present
        if no taxes apply """
        result = {}
        base_row_total = float(record['base_row_total'] or 0.)
        base_row_total_incl_tax = float(
            record.get('base_row_total_incl_tax') or base_row_total)
        qty_ordered = float(record['qty_ordered'])
        if self.options.tax_include:
            result['price_unit'] = base_row_total_incl_tax / qty_ordered
        else:
            result['price_unit'] = base_row_total / qty_ordered
        return result
