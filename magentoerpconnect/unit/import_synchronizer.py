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
from openerp.addons.connector.queue.job import job
from openerp.addons.connector.connector import ConnectorUnit
from openerp.addons.connector.unit.synchronizer import ImportSynchronizer
from ..backend import magento
from ..connector import get_environment, add_checkpoint

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
        """ Call the convert on the Mapper so the converted record can
        be obtained using mapper.data or mapper.data_for_create"""
        self.mapper.convert(self.magento_record)

    def _validate_data(self, data):
        """ Check if the values to import are correct

        Pro-actively check before the ``_create`` or
        ``_update`` if some fields are missing or invalid.

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

        self._map_data()

        openerp_id = self._get_openerp_id()
        if openerp_id:
            record = self.mapper.data
            # special check on data before import
            self._validate_data(record)
            self._update(openerp_id, record)
        else:
            record = self.mapper.data_for_create
            # special check on data before import
            self._validate_data(record)
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


class DirectBatchImport(BatchImportSynchronizer):
    """ Import the records directly, without delaying the jobs. """
    _model_name = None

    def _import_record(self, record_id):
        """ Import the record directly """
        import_record(self.session,
                      self.model._name,
                      self.backend_record.id,
                      record_id)


class DelayedBatchImport(BatchImportSynchronizer):
    """ Delay import of the records """
    _model_name = None

    def _import_record(self, record_id, **kwargs):
        """ Delay the import of the records"""
        import_record.delay(self.session,
                            self.model._name,
                            self.backend_record.id,
                            record_id,
                            **kwargs)


@magento
class SimpleRecordImport(MagentoImportSynchronizer):
    """ Import one Magento Website """
    _model_name = [
            'magento.website',
            'magento.res.partner.category',
        ]


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
            record = self.mapper.convert(lang_record).data

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
class AddCheckpoint(ConnectorUnit):
    """ Add a connector.checkpoint on the underlying model
    (not the magento.* but the _inherits'ed model) """

    _model_name = ['magento.product.product',
                   'magento.product.category',
                   'magento.store',
                   ]

    def run(self, openerp_binding_id):
        binding = self.session.browse(self.model._name,
                                      openerp_binding_id)
        record = binding.openerp_id
        add_checkpoint(self.session,
                       record._model._name,
                       record.id,
                       self.backend_record.id)


@job
def import_batch(session, model_name, backend_id, filters=None):
    """ Prepare a batch import of records from Magento """
    env = get_environment(session, model_name, backend_id)
    importer = env.get_connector_unit(BatchImportSynchronizer)
    importer.run(filters=filters)


@job
def import_record(session, model_name, backend_id, magento_id):
    """ Import a record from Magento """
    env = get_environment(session, model_name, backend_id)
    importer = env.get_connector_unit(MagentoImportSynchronizer)
    importer.run(magento_id)
