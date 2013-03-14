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
from openerp.addons.connector.connector import Environment
from openerp.addons.connector.unit.synchronizer import ImportSynchronizer
from openerp.addons.connector.unit.backend_adapter import BackendAdapter
from ..backend import magento
from ..connector import get_environment

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

    def _has_to_skip(self):
        """ Return True if the import can be skipped """
        return False

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

    def _context(self, **kwargs):
        if not 'lang' in kwargs:
            lang = self.backend_record.default_lang_id
            if lang:
                kwargs['lang'] = lang.code
        return dict(self.session.context, connector_no_export=True, **kwargs)

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

        if self._has_to_skip():
            return

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

    def run(self, filters=None, from_date=None):
        """ Run the synchronization """
        record_ids = self.backend_adapter.search(filters, from_date)
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
            'magento.product.product',
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
            'magento.product.product',
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
        record_ids = self.backend_adapter.search(filters)
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
        addresses_adapter  = self.get_connector_unit_for_model(BackendAdapter,
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

    def _create(self, data):
        """ Create the OpenERP record """
        if self.link_with_partner:
            data['openerp_id'] = self.partner_id
        else:
            data['parent_id'] = self.partner_id
        data['magento_partner_id'] = self.magento_partner_id
        return super(AddressImport, self)._create(data)

    def _update(self, openerp_id, data):
        """ Update an OpenERP record """
        data['parent_id'] = self.partner_id
        data['magento_partner_id'] = self.magento_partner_id
        return super(AddressImport, self)._update(openerp_id, data)


@magento
class ProductCategoryBatchImport(BatchImportSynchronizer):
    """ Import the Magento Product Categories.

    For every partner in the list, a delayed job is created.
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
        assert not filters, "filters are not used for product categories"
        base_priority = 10
        def import_nodes(tree, level=0):
            for node_id, children in tree.iteritems():
                # By changing the priority, the top level category has
                # more chance to be imported before the childrens.
                # However, importers have to ensure that their parent is
                # there and import it if it doesn't exist
                self._import_record(node_id, priority=base_priority+level)
                import_nodes(children, level=level+1)
        tree = self.backend_adapter.tree()
        import_nodes(tree)


class TranslatableImport(object):
    """ Mixin for imports with translations """

    def _get_magento_data(self, storeview_id=None):
        """ Return the raw Magento data for ``self.magento_id`` """
        return self.backend_adapter.read(self.magento_id, storeview_id)

    def _after_import(self, openerp_id):
        super(TranslatableImport, self)._after_import(openerp_id)
        session = self.session
        storeview_obj = session.pool.get('magento.storeview')
        model_fields_obj = session.pool.get('ir.model.fields')
        cr, uid, context = (session.cr,
                            session.uid,
                            session.context)
        storeview_ids = storeview_obj.search(
                cr, uid,
                [('backend_id', '=', self.backend_record.id)],
                context=context)
        default_lang = self.backend_record.default_lang_id
        storeviews = storeview_obj.browse(cr, uid,
                                          storeview_ids,
                                          context=context)
        lang_storeviews = [sv for sv in storeviews
                           if sv.lang_id and sv.lang_id != default_lang]
        if not lang_storeviews:
            return

        fields = self.model.fields_get(cr, uid, context=context)
        translatable_fields = [field for field, attrs in fields.iteritems()
                               if attrs.get('translate')]

        for storeview in lang_storeviews:
            context = self._context(lang=storeview.lang_id.code)
            lang_record = self._get_magento_data(storeview.magento_id)
            record = self.mapper.convert(lang_record)

            data = dict((field, value) for field, value in record.iteritems()
                        if field in translatable_fields)
            self.model.write(cr, uid, openerp_id, data, context=context)


@magento
class SaleOrderBatchImport(DelayedBatchImport):
    _model_name = ['magento.sale.order']
    def run(self, filters=None):
        """ Run the synchronization """
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
class SaleOrderImport(MagentoImportSynchronizer):
    _model_name = ['magento.sale.order']
    def _import_dependencies(self):
        record = self.magento_record
        if 'customer_id' in record:
            binder = self.get_binder_for_model('magento.res.partner')
            if binder.to_openerp(record['customer_id']) is None:
                importer = self.get_connector_unit_for_model(MagentoImportSynchronizer,
                                                             'magento.res.partner')
                importer.run(record['customer_id'])

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
class ProductImport(TranslatableImport, MagentoImportSynchronizer):
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


@magento
class ProductCategoryImport(TranslatableImport, MagentoImportSynchronizer):
    _model_name = ['magento.product.category']

    def _import_dependencies(self):
        """ Import the dependencies for the record"""
        record = self.magento_record
        env = self.environment
        # import parent category
        # the root category has a 0 parent_id
        if record.get('parent_id'):
            binder = self.get_binder_for_model()
            if binder.to_openerp(record['parent_id']) is None:
                importer = env.get_connector_unit(MagentoImportSynchronizer)
                importer.run(record['parent_id'])


@job
def import_batch(session, model_name, backend_id, filters=None, from_date=None):
    """ Prepare a batch import of records from Magento """
    env = get_environment(session, model_name, backend_id)
    importer = env.get_connector_unit(BatchImportSynchronizer)
    importer.run(filters)

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
def import_partners_since(session, model_name, backend_id, since_date=None):
    """ Prepare the import of partners modified on Magento """
    # FIXME: this may run a long time after the user has clicked the
    # import button -> the use of datetime.now() should be done in the
    # method called by the button, and not in the async. processing
    # see what is done by the import_sale_orders
    env = get_environment(session, model_name, backend_id)
    importer = env.get_connector_unit(BatchImportSynchronizer)
    now_fmt = datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
    filters = {}
    if since_date:
        since_fmt = since_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        # updated_at include the created records
        filters['updated_at'] = {'from': since_fmt}
    importer.run(filters=filters)
    session.pool.get('magento.backend').write(
            session.cr,
            session.uid,
            backend_id,
            {'import_partners_since': now_fmt},
            context=session.context)
