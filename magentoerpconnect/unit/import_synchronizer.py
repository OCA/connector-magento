# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
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
from datetime import datetime
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.addons.connector.queue.job import job
from openerp.addons.connector.exception import FailedJobError, NothingToDoJob
from openerp.addons.connector.connector import Environment, ConnectorUnit
from openerp.addons.connector.unit.synchronizer import ImportSynchronizer
from openerp.addons.connector.unit.backend_adapter import BackendAdapter
from openerp.addons.connector.unit.mapper import ImportMapper
from ..backend import magento
from ..connector import get_environment
from ..exception import OrderImportRuleRetry

_logger = logging.getLogger(__name__)


class MagentoImportSynchronizer(ImportSynchronizer):
    """ Base importer for Magento """

    def __init__(self, environment):
        """
        :param environment: current environment (backend, session, ...)
        :type environment: :py:class:`connector.connector.Environment`
        """
        super(MagentoImportSynchronizer, self).__init__(environment)
        self.magento_id = None
        self.magento_record = None

    def _get_magento_data(self):
        """ Return the raw Magento data for ``self.magento_id`` """
        return self.backend_adapter.read(self.magento_id)

    def _before_import(self):
        """ Hook called before the import, when we have the Magento
        data"""


    def _import_dependencies(self):
        """ Import the dependencies for the record"""
        return

    def _map_data(self):
        """ Return the external record converted to OpenERP """
        return self.mapper.convert(self.magento_record)

    def _validate_data(self, data):
        """ Check if the values to import are correct

        Pro-actively check before the ``Model.create`` or
        ``Model.update`` if some fields are missing

        Raise `InvalidDataError`
        """
        return

    def _get_openerp_id(self):
        """Return the openerp id from the magento id"""
        return self.binder.to_openerp(self.magento_id)

    def _context(self):
        context = self.session.context.copy()
        context['connector_no_export'] = True
        return context

    def _create(self, data):
        """ Create the OpenERP record """
        openerp_id = self.model.create(self.session.cr,
                                       self.session.uid,
                                       data,
                                       context=self._context())
        _logger.debug('%s %d created from magento %s',
                      self.model._name, openerp_id, self.magento_id)
        return openerp_id

    def _update(self, openerp_id, data):
        """ Update an OpenERP record """
        self.model.write(self.session.cr,
                         self.session.uid,
                         openerp_id,
                         data,
                         context=self._context())
        _logger.debug('%s %d updated from magento %s',
                      self.model._name, openerp_id, self.magento_id)
        return

    def _after_import(self, openerp_id):
        """ Hook called at the end of the import """
        return

    def run(self, magento_id):
        """ Run the synchronization

        :param magento_id: identifier of the record on Magento
        """
        self.magento_id = magento_id
        self.magento_record = self._get_magento_data()

        self._before_import()

        # import the missing linked resources
        self._import_dependencies()

        record = self._map_data()

        # special check on data before import
        self._validate_data(record)

        openerp_id = self._get_openerp_id()

        if openerp_id:
            self._update(openerp_id, record)
        else:
            openerp_id = self._create(record)

        self.binder.bind(self.magento_id, openerp_id)

        self._after_import(openerp_id)


class BatchImportSynchronizer(ImportSynchronizer):
    """ The role of a BatchImportSynchronizer is to search for a list of
    items to import, then it can either import them directly or delay
    the import of each item separately.
    """

    def run(self, filters=None):
        """ Run the synchronization """
        record_ids = self.backend_adapter.search(filters)
        for record_id in record_ids:
            self._import_record(record_id)

    def _import_record(self, record_id):
        """ Import a record directly or delay the import of the record """
        raise NotImplementedError


@magento
class DirectBatchImport(BatchImportSynchronizer):
    """ Import the Magento Websites, Stores, Storeviews

    They are imported directly because this is a rare and fast operation,
    performed from the UI.
    """
    _model_name = [
            'magento.website',
            'magento.store',
            'magento.storeview',
            ]

    def _import_record(self, record_id):
        """ Import the record directly """
        import_record(self.session,
                      self.model._name,
                      self.backend_record.id,
                      record_id)


@magento
class DelayedBatchImport(BatchImportSynchronizer):
    """ Delay import of the records """
    _model_name = [
            'magento.res.partner.category',
            ]

    def _import_record(self, record_id):
        """ Delay the import of the records"""
        import_record.delay(self.session,
                            self.model._name,
                            self.backend_record.id,
                            record_id)


@magento
class SimpleRecordImport(MagentoImportSynchronizer):
    """ Import one Magento Website """
    _model_name = [
            'magento.website',
            'magento.store',
            'magento.storeview',
            'magento.res.partner.category',
        ]


@magento
class PartnerBatchImport(BatchImportSynchronizer):
    """ Import the Magento Partners.

    For every partner in the list, a delayed job is created.
    """
    _model_name = ['magento.res.partner']

    def _import_record(self, record_id):
        """ Delay a job for the import """
        import_record.delay(self.session,
                            self.model._name,
                            self.backend_record.id,
                            record_id)

    def run(self, filters=None):
        """ Run the synchronization """
        from_date = filters.pop('from_date', None)
        magento_website_ids = [filters.pop('magento_website_id')]
        record_ids = self.backend_adapter.search(filters,
                                                 from_date,
                                                 magento_website_ids)
        _logger.info('search for magento partners %s returned %s',
                     filters, record_ids)
        for record_id in record_ids:
            self._import_record(record_id)


@magento
class PartnerImport(MagentoImportSynchronizer):
    _model_name = ['magento.res.partner']

    def _import_dependencies(self):
        """ Import the dependencies for the record"""
        record = self.magento_record

        # import customer groups
        binder = self.get_binder_for_model('magento.res.partner.category')
        if binder.to_openerp(record['group_id']) is None:
            importer = self.get_connector_unit_for_model(MagentoImportSynchronizer,
                                                         'magento.res.partner.category')
            importer.run(record['group_id'])

    def _after_import(self, magento_res_partner_openerp_id):
        """ Import the addresses """
        addresses_adapter = self.get_connector_unit_for_model(BackendAdapter,
                                                              'magento.address')
        mag_address_ids = addresses_adapter.search(
                {'customer_id': {'eq': self.magento_id}})
        if not mag_address_ids:
            return
        importer = self.get_connector_unit_for_model(MagentoImportSynchronizer,
                                                     'magento.address')
        partner_row = self.model.read(self.session.cr,
                                      self.session.uid,
                                      magento_res_partner_openerp_id,
                                      ['openerp_id'],
                                      context=self.session.context)
        res_partner_openerp_id = partner_row['openerp_id'][0]
        mag_addresses = {} # mag_address_id -> True if address is linked to existing partner,
                           #                   False otherwise
        if len(mag_address_ids) == 1:
            mag_addresses[mag_address_ids[0]] = True
        else:
            billing_address = False
            for address_id in mag_address_ids:
                magento_record = addresses_adapter.read(address_id)

                if magento_record['is_default_billing']:
                    mag_addresses[address_id] = True
                    billing_address = True
                else:
                    mag_addresses[address_id] = False
            if not billing_address:
                mag_addresses[min(mag_addresses)] = True
        for address_id, to_link in mag_addresses.iteritems():
            importer.run(address_id,
                         magento_res_partner_openerp_id,
                         res_partner_openerp_id,
                         to_link)


@magento
class AddressImport(MagentoImportSynchronizer):
    _model_name = ['magento.address']

    def run(self, magento_id, magento_partner_id, partner_id, link_with_partner):
        """ Run the synchronization """
        self.partner_id = partner_id
        self.magento_partner_id = magento_partner_id
        self.link_with_partner = link_with_partner
        super(AddressImport, self).run(magento_id)

    def _map_data(self):
        """ Return the external record converted to OpenERP """
        data = super(AddressImport, self)._map_data()
        if self.link_with_partner:
            data['openerp_id'] = self.partner_id
        else:
            data['parent_id'] = self.partner_id
            partner = self.session.browse('res.partner',
                                          self.partner_id)
            data['lang'] = partner.lang
        data['magento_partner_id'] = self.magento_partner_id
        return data


@magento
class ProductCategoryBatchImport(BatchImportSynchronizer):
    """ Import the Magento Product Categories.

    For every product category in the list, a delayed job is created.
    A priority is set on the jobs according to their level to rise the
    chance to have the top level categories imported first.
    """
    _model_name = ['magento.product.category']

    def _import_record(self, magento_id, priority=None):
        """ Delay a job for the import """
        import_record.delay(self.session,
                            self.model._name,
                            self.backend_record.id,
                            magento_id,
                            priority=priority)

    def run(self, filters=None):
        """ Run the synchronization """
        from_date = filters.pop('from_date', None)
        if from_date is not None:
            updated_ids = self.backend_adapter.search(filters, from_date)
        else:
            updated_ids = None

        base_priority = 10
        def import_nodes(tree, level=0):
            for node_id, children in tree.iteritems():
                # By changing the priority, the top level category has
                # more chance to be imported before the childrens.
                # However, importers have to ensure that their parent is
                # there and import it if it doesn't exist
                if updated_ids is None or node_id in updated_ids:
                    self._import_record(node_id, priority=base_priority+level)
                import_nodes(children, level=level+1)
        tree = self.backend_adapter.tree()
        import_nodes(tree)


@magento
class ProductBatchImport(BatchImportSynchronizer):
    """ Import the Magento Products.

    For every product category in the list, a delayed job is created.
    Import from a date
    """
    _model_name = ['magento.product.product']

    def _import_record(self, magento_id, priority=None):
        """ Delay a job for the import """
        import_record.delay(self.session,
                            self.model._name,
                            self.backend_record.id,
                            magento_id)

    def run(self, filters=None):
        """ Run the synchronization """
        from_date = filters.pop('from_date', None)
        record_ids = self.backend_adapter.search(filters, from_date)
        _logger.info('search for magento products %s returned %s',
                     filters, record_ids)
        for record_id in record_ids:
            self._import_record(record_id)


@magento
class TranslationImporter(ImportSynchronizer):
    """ Import translations for a record.

    Usually called from importers, in ``_after_import``.
    For instance from the products and products' categories importers.
    """

    _model_name = ['magento.product.category',
                   'magento.product.product',
                   ]

    def _get_magento_data(self, storeview_id=None):
        """ Return the raw Magento data for ``self.magento_id`` """
        return self.backend_adapter.read(self.magento_id, storeview_id)

    def run(self, magento_id, openerp_id):
        self.magento_id = magento_id
        session = self.session
        storeview_ids = session.search(
                'magento.storeview',
                [('backend_id', '=', self.backend_record.id)])
        storeviews = session.browse('magento.storeview', storeview_ids)
        default_lang = self.backend_record.default_lang_id
        lang_storeviews = [sv for sv in storeviews
                           if sv.lang_id and sv.lang_id != default_lang]
        if not lang_storeviews:
            return

        # find the translatable fields of the model
        fields = self.model.fields_get(session.cr, session.uid,
                                       context=session.context)
        translatable_fields = [field for field, attrs in fields.iteritems()
                               if attrs.get('translate')]

        for storeview in lang_storeviews:
            lang_record = self._get_magento_data(storeview.magento_id)
            record = self.mapper.convert(lang_record)

            data = dict((field, value) for field, value in record.iteritems()
                        if field in translatable_fields)

            context = session.context.copy()
            context['lang'] = storeview.lang_id.code
            self.model.write(session.cr,
                             session.uid,
                             openerp_id,
                             data,
                             context=context)


@magento
class SaleOrderBatchImport(DelayedBatchImport):
    _model_name = ['magento.sale.order']
    def run(self, filters=None):
        """ Run the synchronization """
        if filters is None:
            filters = {}
        filters['state'] = {'neq': 'canceled'}
        from_date = filters.pop('from_date', None)
        magento_storeview_ids = [filters.pop('magento_storeview_id')]
        record_ids = self.backend_adapter.search(filters,
                                                 from_date,
                                                 magento_storeview_ids)
        _logger.info('search for magento saleorders %s  returned %s',
                     filters, record_ids)
        for record_id in record_ids:
            self._import_record(record_id)


@magento
class SaleImportRule(ConnectorUnit):
    _model_name = ['magento.sale.order']

    def _rule_always(self, record):
        """ Always import the order """
        return True

    def _rule_never(self, record):
        """ Never import the order """
        raise NothingToDoJob('Orders with payment method %s '
                             'are never imported.' %
                             record['payment']['method'])

    def _rule_paid(self, record):
        """ Import the order only if it has received a payment """
        if not record.get('payment', {}).get('amount_paid'):
            raise OrderImportRuleRetry('The order has not been paid.\n'
                                       'Will retry later.')

    _rules = {'always': _rule_always,
              'paid': _rule_paid,
              'never': _rule_never,
              }

    def _rule_global(self, record):
        """ Rule always executed, whichever is the selected rule """
        # the order has been canceled since the job has been created
        if record['state'] == 'canceled':
            raise NothingToDoJob('Order %s canceled' % record['increment_id'])

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
                    "- Go to 'Sales > Configuration > Sales > Customer Payment Method\n"
                    "- Create a new Payment Method with name '%s'\n"
                    "-Eventually  link the Payment Method to an existing Workflow "
                    "Process or create a new one." % (payment_method,
                                                      payment_method))
        method = session.browse('payment.method', method_ids[0])
        self._rule_global(record)
        self._rules[method.import_rule](self, record)


@magento
class SaleOrderImport(MagentoImportSynchronizer):
    _model_name = ['magento.sale.order']

    def _import_customer_group(self, group_id):
        binder = self.get_binder_for_model('magento.res.partner.category')
        if binder.to_openerp(group_id) is None:
            importer = self.get_connector_unit_for_model(MagentoImportSynchronizer,
                                                         'magento.res.partner.category')
            importer.run(group_id)

    def _before_import(self):
        rules = self.get_connector_unit_for_model(SaleImportRule)
        rules.check(self.magento_record)

    def _import_addresses(self):
        record = self.magento_record
        sess = self.session

        # Magento allows to create a sale order not registered as a user
        is_guest_order = bool(int(record.get('customer_is_guest', 0)))

        # For a guest order or when magento does not provide customer_id
        # on a non-guest order (it happens, Magento inconsistencies are
        # common)
        if (is_guest_order or not record.get('customer_id')):

            # sometimes we don't have website_id...
            if record.get('website_id'):
                website_binder = self.get_binder_for_model('magento.website')
                oe_website_id = website_binder.to_openerp(record['website_id'])
            else:
                # deduce it from the store
                store_binder = self.get_binder_for_model('magento.store')
                oe_store_id = store_binder.to_openerp(record['store_id'])
                store = sess.browse('magento.store', oe_store_id)
                oe_website_id = store.website_id.id
                # "fix" the record
                record['website_id'] = store.website_id.magento_id

            # search an existing partner with the same email
            partner_ids = sess.search('magento.res.partner',
                                      [('emailid', '=', record['customer_email']),
                                       ('website_id', '=', oe_website_id)])

            # if we have found one, we "fix" the record with the magento
            # customer id
            if partner_ids:
                partner = sess.read('magento.res.partner',
                                    partner_ids[0],
                                    ['magento_id'])
                record['customer_id'] = partner['magento_id']

            # no partner matching, it means that we have to consider it
            # as a guest order
            else:
                is_guest_order = True

        partner_binder = self.get_binder_for_model('magento.res.partner')
        if is_guest_order:
            # ensure that the flag is correct in the record
            record['customer_is_guest'] = True

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
            mapper = self.get_connector_unit_for_model(ImportMapper,
                                                      'magento.res.partner')
            oe_record = mapper.convert(customer_record)
            oe_record['guest_customer'] = True
            partner_bind_id = sess.create('magento.res.partner', oe_record)
        else:

            # we always update the customer when importing an order
            importer = self.get_connector_unit_for_model(MagentoImportSynchronizer,
                                                         'magento.res.partner')
            importer.run(record['customer_id'])
            partner_bind_id = partner_binder.to_openerp(record['customer_id'])

        partner_id = sess.read('magento.res.partner',
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
            oe_address = addr_mapper.convert(address_record)
            oe_address.update(addresses_defaults)
            address_bind_id = sess.create('magento.address', oe_address)
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

    def _map_data(self):
        """ Return the external record converted to OpenERP """
        data = super(SaleOrderImport, self)._map_data()
        assert self.partner_id, "self.partner_id should have been defined in SaleOrderImport._import_addresses"
        assert self.partner_invoice_id, "self.partner_id should have been defined in SaleOrderImport._import_addresses"
        assert self.partner_shipping_id, "self.partner_id should have been defined in SaleOrderImport._import_addresses"
        data['partner_id'] = self.partner_id
        data['partner_invoice_id'] = self.partner_invoice_id
        data['partner_shipping_id'] = self.partner_shipping_id
        return data

    def _import_dependencies(self):
        record = self.magento_record

        self._import_addresses()

        prod_binder = self.get_binder_for_model('magento.product.product')
        prod_importer = self.get_connector_unit_for_model(MagentoImportSynchronizer,
                                                          'magento.product.product')
        for line in record.get('items', []):
            _logger.info('line: %s', line)
            if 'product_id' in line and prod_binder.to_openerp(line['product_id']) is None:
                prod_importer.run(line['product_id'])


@magento
class SaleOrderLineImport(MagentoImportSynchronizer):
    _model_name = ['magento.sale.order.line']
    def _import_dependencies(self):
        record = self.magento_record
        if 'item_id' in record:
            binder = self.get_binder_for_model('magento.product.product')
            if binder.to_openerp(record['item_id']) is None:
                importer = self.get_connector_unit_for_model(MagentoImportSynchronizer,
                                                             'magento.product.product')
                importer.run(record['item_id'])


@magento
class ProductImport(MagentoImportSynchronizer):
    _model_name = ['magento.product.product']

    def _import_dependencies(self):
        """ Import the dependencies for the record"""
        record = self.magento_record
        # import related categories
        binder = self.get_binder_for_model('magento.product.category')
        for mag_category_id in record['categories']:
            if binder.to_openerp(mag_category_id) is None:
                importer = self.get_connector_unit_for_model(
                                MagentoImportSynchronizer,
                                model='magento.product.category')
                importer.run(mag_category_id)

    def _after_import(self, openerp_id):
        """ Hook called at the end of the import """
        translation_importer = self.get_connector_unit_for_model(
                TranslationImporter, self.model._name)
        translation_importer.run(self.magento_id, openerp_id)


@magento
class ProductCategoryImport(MagentoImportSynchronizer):
    _model_name = ['magento.product.category']

    def _import_dependencies(self):
        """ Import the dependencies for the record"""
        record = self.magento_record
        env = self.environment
        # import parent category
        # the root category has a 0 parent_id
        if record.get('parent_id'):
            binder = self.get_binder_for_model()
            parent_id = record['parent_id']
            if binder.to_openerp(parent_id) is None:
                importer = env.get_connector_unit(MagentoImportSynchronizer)
                importer.run(parent_id)

    def _after_import(self, openerp_id):
        """ Hook called at the end of the import """
        translation_importer = self.get_connector_unit_for_model(
                TranslationImporter, self.model._name)
        translation_importer.run(self.magento_id, openerp_id)


@job
def import_batch(session, model_name, backend_id, filters=None):
    """ Prepare a batch import of records from Magento """
    env = get_environment(session, model_name, backend_id)
    importer = env.get_connector_unit(BatchImportSynchronizer)
    importer.run(filters=filters)


@job
def sale_order_import_batch(session, model_name, backend_id, filters=None):
    """ Prepare a batch import of records from Magento """
    if filters is None:
        filters = {}
    assert 'magento_storeview_id' in filters, 'Missing information about Magento Storeview'
    env = get_environment(session, model_name, backend_id)
    importer = env.get_connector_unit(SaleOrderBatchImport)
    importer.run(filters)


@job
def import_record(session, model_name, backend_id, magento_id):
    """ Import a record from Magento """
    env = get_environment(session, model_name, backend_id)
    importer = env.get_connector_unit(MagentoImportSynchronizer)
    importer.run(magento_id)


@job
def partner_import_batch(session, model_name, backend_id, filters=None):
    """ Prepare the import of partners modified on Magento """
    if filters is None:
        filters = {}
    assert 'magento_website_id' in filters, (
            'Missing information about Magento Website')
    env = get_environment(session, model_name, backend_id)
    importer = env.get_connector_unit(PartnerBatchImport)
    importer.run(filters=filters)
