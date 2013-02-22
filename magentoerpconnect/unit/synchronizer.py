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
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
import openerp.addons.connector as connector
from .backend_adapter import MagentoLocation
from ..backend import magento

_logger = logging.getLogger(__name__)



class MagentoExportSynchronizer(connector.ExportSynchronizer):
    """ Base exporter for Magento """


class MagentoImportSynchronizer(connector.ImportSynchronizer):
    """ Base importer for Magento """

    _metadata_model = None

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

    def _map_metadata(self):
        """ Return the metadata for the record converted to OpenERP """
        if self._metadata_model is None:
            return
        mapper = connector.Environment(
                self.backend_record,
                self.session,
                self._metadata_model).get_connector_unit(connector.ImportMapper)
        return mapper.convert(self.magento_record)

    def _validate_data(self, data):
        """ Check if the values to import are correct

        Pro-actively check before the ``Model.create`` or
        ``Model.update`` if some fields are missing

        Raise `InvalidDataError`
        """
        return

    def _create(self, data):
        """ Create the OpenERP record """
        openerp_id = self.model.create(self.session.cr,
                                       self.session.uid,
                                       data,
                                       self.session.context)
        _logger.debug('openerp_id: %d created', openerp_id)
        return openerp_id

    def _update(self, openerp_id, data):
        """ Update an OpenERP record """
        self.model.write(self.session.cr,
                         self.session.uid,
                         openerp_id,
                         data,
                         self.session.context)
        _logger.debug('openerp_id: %d updated', openerp_id)
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
        metadata = self._map_metadata()

        # special check on data before import
        self._validate_data(record)

        openerp_id = self.binder.to_openerp(self.magento_id)

        if openerp_id:
            self._update(openerp_id, record)
        else:
            openerp_id = self._create(record)

        self.binder.bind(self.magento_id, openerp_id, metadata=metadata)


class BatchImportSynchronizer(connector.ImportSynchronizer):
    """ The role of a BatchImportSynchronizer is to search for a list of
    items to import, then it can either import them directly or delay
    the import of each item separately.
    """

    def run(self, filters=None):
        """ Run the synchronization """
        record_ids = self.backend_adapter.search(filters)
        for record_id in record_ids:
            self._import_record(record_id)

    def _import_record(self, record):
        """ Import a record directly or delay the import of the record """
        raise NotImplementedError


# imported after base classes to avoid circular imports
from ..queue import job


@magento
class SimpleBatchImport(BatchImportSynchronizer):
    """ Import the Magento Websites, Stores, Storeviews

    They are imported directly because this is a rare and fast operation,
    performed from the UI.
    """
    _model_name = [
            'magento.website',
            'magento.store',
            'magento.storeview',
            ]

    def _import_record(self, record):
        """ Import the record directly """
        job.import_record(self.session,
                          self.backend_record.id,
                          self.model._name,
                          record)


@magento
class WebsiteImport(MagentoImportSynchronizer):
    """ Import one Magento Website """
    _model_name = [
            'magento.website',
            'magento.store',
            'magento.storeview'
        ]


@magento
class PartnerBatchImport(BatchImportSynchronizer):
    """ Import the Magento Partners.

    For every partner in the list, a delayed job is created.
    """
    _model_name = ['res.partner']

    def _import_record(self, record):
        """ Delay a job for the import """
        job.import_partner.delay(self.session,
                                 self.backend_record.id,
                                 record)

    def run(self, since=None, filters=None):
        """ Run the synchronization """
        # Magento API does not support OR, so we search 2 times
        # one time > created_at and a second > updated_at
        if filters is None:
            filters = {}
        if since:
            since_fmt = since.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            record_ids = []

            for at in ('created_at', 'updated_at'):
                since_filter = {at: {'from': since_fmt}}
                since_filter.update(filters)
                record_ids = self.backend_adapter.search(since_filter)

        for record_id in record_ids:
            self._import_record(record_id)

@magento
class PartnerImport(MagentoImportSynchronizer):
    _model_name = ['res.partner']
    _metadata_model = 'magento.res.partner'


"""
TODO

Notes on the partner export.

2 synchronizers should be created:
    on 'res.partner'
    on 'magento.res.partner'

The latter has a dependency on 'res.partner', so if the partner
is not already exported, it export it.

The 'res.partner' export should do an export per website in
'magento.res.partner'

"""
