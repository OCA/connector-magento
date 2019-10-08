# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import _
from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create
from odoo.addons.connector.exception import MappingError
import json
import uuid


class AccountPaymentImportMapper(Component):
    _name = 'magento.account.payment.import.mapper'
    _inherit = 'magento.import.mapper'
    _apply_on = 'magento.account.payment'

    direct = [
        ('account_status', 'account_status'),
        ('amount_ordered', 'amount_ordered'),
        ('amount_paid', 'amount_paid'),
        ('amount_paid', 'amount'),
        ('last_trans_id', 'last_trans_id'),
        ('last_trans_id', 'communication'),
        ('entity_id', 'external_id'),
    ]

    def _generate_payment_reference(self, record):
        return "%s.%s.%s" % (self.backend_record.id, record['entity_id'],
                             record['last_trans_id'] if 'last_trans_id' in record else str(uuid.uuid4()))

    @mapping
    def name(self, record):
        return {'name': 'Imported payment for order %s' % self.options.order_binding.name}

    @mapping
    def rounding_difference(self, record):
        if 0.01 > abs(record['amount_paid'] - self.options.order_binding.amount_total) > 0 and self.backend_record.rounding_diff_account_id:
            return {
               'payment_difference_handling': 'reconcile',
               'writeoff_account_id': self.backend_record.rounding_diff_account_id.id
            }

    @ mapping
    def additional_information(self, record):
        if not 'additional_information' in record:
            return {}
        return {'additional_information': json.dumps(record['additional_information'], indent=4)}

    @mapping
    def payment_ref(self, record):
        ref = self._generate_payment_reference(record)
        return {'payment_reference': ref}

    @mapping
    def payment_date(self, record):
        return {'payment_date': self.options.order_binding.date_order}

    @mapping
    def payment_vars(self, record):
        payment_method = record['method']
        binder = self.binder_for('magento.account.payment.mode')
        method = binder.to_internal(payment_method, unwrap=True)
        if not method:
            raise MappingError(
                "The configuration is missing for the Payment Mode '%s'.\n\n"
                "Resolution:\n"
                "- Create a new Payment Method Mapping" % (payment_method,))
        if method.bank_account_link == 'variable' or not method.fixed_journal_id:
            raise MappingError(
                "The configuration for the Payment Mode '%s'.\n\n"
                "is wrong. Payment Mode must be configured with a fixed journal !" % (payment_method,))
        return {
            'payment_type': method.payment_method_id.payment_type,
            'partner_type': 'customer',
            'payment_method_id': method.payment_method_id.id,
            'journal_id': method.fixed_journal_id.id
        }

    @mapping
    @only_create
    def partner_id(self, record):
        return {'partner_id': self.options.order_binding.partner_id.id}

    @mapping
    @only_create
    def order_id(self, record):
        return {'order_id': self.options.order_binding.odoo_id.id}

    @mapping
    @only_create
    def odoo_id(self, record):
        ref = self._generate_payment_reference(record)
        return {'odoo_id': self.env['account.payment'].search([('payment_reference', '=', ref)], limit=1).id}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}


class AccountPaymentImporter(Component):
    _name = 'magento.account.payment.importer'
    _inherit = 'magento.importer'
    _apply_on = 'magento.account.payment'

    def _after_import(self, binding):
        # Post Payment
        if binding.state == 'draft':
            binding.odoo_id.post()

    def run_with_data(self, record, order_binding, force=False):
        self.force = force
        self.external_id = record['entity_id']

        lock_name = 'import({}, {}, {}, {})'.format(
            self.backend_record._name,
            self.backend_record.id,
            self.work.model_name,
            str(self.external_id),
        )

        self.magento_record = record
        self.order_binding = order_binding

        skip = self._must_skip()
        if skip:
            return skip
        binding = self._get_binding()

        if not force and self._is_uptodate(binding):
            return _('Already up-to-date.')

        # Keep a lock on this import until the transaction is committed
        # The lock is kept since we have detected that the informations
        # will be updated into Odoo
        self.advisory_lock_or_retry(lock_name)
        self._before_import()

        # import the missing linked resources
        self._import_dependencies()

        map_record = self._map_data()

        if binding:
            record = self._update_data(map_record, order_binding=order_binding)
            self._update(binding, record)
        else:
            record = self._create_data(map_record, order_binding=order_binding)
            binding = self._create(record)

        self.binder.bind(self.external_id, binding)

        self._after_import(binding)
