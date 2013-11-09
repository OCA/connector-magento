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
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.addons.connector.queue.job import job
from openerp.addons.connector.connector import ConnectorUnit
from openerp.addons.connector.unit.synchronizer import ImportSynchronizer
from openerp.addons.connector.exception import IDMissingInBackend
from ..backend import magento
from ..connector import get_environment, add_checkpoint

_logger = logging.getLogger(__name__)

"""

Importers for Magento.

An import can be skipped if the last sync date is more recent than
the last update in Magento.

They should call the ``bind`` method if the binder even if the records
are already bound, to update the last sync date.

"""

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

    def _is_uptodate(self, binding_id):
        """Return True if the import should be skipped because
        it is already up-to-date in OpenERP"""
        assert self.magento_record
        if not self.magento_record.get('updated_at'):
            return  # no update date on Magento, always import it.
        if not binding_id:
            return  # it does not exist so it shoud not be skipped
        binding = self.session.browse(self.model._name, binding_id)
        sync = binding.sync_date
        if not sync:
            return
        fmt = DEFAULT_SERVER_DATETIME_FORMAT
        sync_date = datetime.strptime(sync, fmt)
        magento_date = datetime.strptime(self.magento_record['updated_at'], fmt)
        # if the last synchronization date is greater than the last
        # update in magento, we skip the import.
        # Important: at the beginning of the exporters flows, we have to
        # check if the magento_date is more recent than the sync_date
        # and if so, schedule a new import. If we don't do that, we'll
        # miss changes done in Magento
        return magento_date < sync_date

    def _import_dependencies(self):
        """ Import the dependencies for the record"""
        return

    def _map_data(self):
        """ Returns an instance of
        :py:class:`~openerp.addons.connector.unit.mapper.MapRecord`

        """
        return self.mapper.map_record(self.magento_record)

    def _validate_data(self, data):
        """ Check if the values to import are correct

        Pro-actively check before the ``_create`` or
        ``_update`` if some fields are missing or invalid.

        Raise `InvalidDataError`
        """
        return

    def _must_skip(self):
        """ Hook called right after we read the data from the backend.

        If the method returns a message giving a reason for the
        skipping, the import will be interrupted and the message
        recorded in the job (if the import is called directly by the
        job, not by dependencies).

        If it returns None, the import will continue normally.

        :returns: None | str | unicode
        """
        return

    def _get_binding_id(self):
        """Return the binding id from the magento id"""
        return self.binder.to_openerp(self.magento_id)

    def _create_data(self, map_record, **kwargs):
        return map_record.values(for_create=True, **kwargs)

    def _create(self, data):
        """ Create the OpenERP record """
        # special check on data before import
        self._validate_data(data)
        with self.session.change_context({'connector_no_export': True}):
            binding_id = self.session.create(self.model._name, data)
        _logger.debug('%s %d created from magento %s',
                      self.model._name, binding_id, self.magento_id)
        return binding_id

    def _update_data(self, map_record, **kwargs):
        return map_record.values(**kwargs)

    def _update(self, binding_id, data):
        """ Update an OpenERP record """
        # special check on data before import
        self._validate_data(data)
        with self.session.change_context({'connector_no_export': True}):
            self.session.write(self.model._name, binding_id, data)
        _logger.debug('%s %d updated from magento %s',
                      self.model._name, binding_id, self.magento_id)
        return

    def _after_import(self, binding_id):
        """ Hook called at the end of the import """
        return

    def run(self, magento_id, force=False):
        """ Run the synchronization

        :param magento_id: identifier of the record on Magento
        """
        self.magento_id = magento_id
        try:
            self.magento_record = self._get_magento_data()
        except IDMissingInBackend:
            return _('Record does no longer exist in Magento')

        skip = self._must_skip()
        if skip:
            return skip

        binding_id = self._get_binding_id()

        if not force and self._is_uptodate(binding_id):
            return _('Already up-to-date.')
        self._before_import()

        # import the missing linked resources
        self._import_dependencies()

        map_record = self._map_data()

        if binding_id:
            record = self._update_data(map_record)
            self._update(binding_id, record)
        else:
            record = self._create_data(map_record)
            binding_id = self._create(record)

        self.binder.bind(self.magento_id, binding_id)

        self._after_import(binding_id)


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
        """ Import a record directly or delay the import of the record.

        Method to implement in sub-classes.
        """
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

    def run(self, magento_id, binding_id):
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
            map_record = self.mapper.map_record(lang_record)
            record = map_record.values()

            data = dict((field, value) for field, value in record.iteritems()
                        if field in translatable_fields)

            ctx = {'connector_no_export': True, 'lang': storeview.lang_id.code}
            with self.session.change_context(ctx):
                self.session.write(self.model._name, binding_id, data)


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
def import_record(session, model_name, backend_id, magento_id, force=False):
    """ Import a record from Magento """
    env = get_environment(session, model_name, backend_id)
    importer = env.get_connector_unit(MagentoImportSynchronizer)
    importer.run(magento_id, force=force)
