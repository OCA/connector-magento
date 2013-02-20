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
import openerp.addons.connector as connector
from .backend_adapter import MagentoLocation
from ..reference import magento

_logger = logging.getLogger(__name__)


class MagentoSynchronizer(connector.Synchronizer):

    _model_name = None  # implement in sub-classes


class MagentoExportSynchronizer(connector.ExportSynchronizer, MagentoSynchronizer):
    """ Base exporter for Magento """


class MagentoImportSynchronizer(connector.ImportSynchronizer, MagentoSynchronizer):
    """ Base importer for Magento """


    def __init__(self, environment, magento_identifier):
        """

        :param environment: current environment (reference, backend, ...)
        :type environment: :py:class:`connector.connector.SynchronizationEnvironment`
        """
        super(MagentoImportSynchronizer, self).__init__(environment)
        self.magento_identifier = magento_identifier
        self.magento_record = None

    def _get_magento_data(self):
        """ Return the raw Magento data for ``self.magento_identifier`` """
        return self.backend_adapter.read(self.magento_identifier)

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

    def run(self):
        """ Run the synchronization

        :param magento_identifier: identifier of the record on Magento
        :type magento_identifier: :py:class:`connector.connector.RecordIdentifier`
        """
        self.magento_record = self._get_magento_data()

        if self._has_to_skip():
            return

        # import the missing linked resources
        self._import_dependencies()

        record = self._map_data()

        # special check on data before import
        self._validate_data(record)

        openerp_id = self.binder.to_openerp(self.backend,
                                            self.magento_identifier)

        if openerp_id:
            self._update(openerp_id, record)
        else:
            openerp_id = self._create(record)
            self.binder.bind(self.backend,
                             self.magento_identifier,
                             openerp_id)


class BatchImportSynchronizer(MagentoSynchronizer):
    """ The role of a BatchImportSynchronizer is to search for a list of
    items to import, then it can either import them directly or delay
    the import of each item separately.
    """

    def run(self, filters=None):
        """ Run the synchronization """
        records = self.backend_adapter.search(filters)
        for record in records:
            self._import_record(record)

    def _import_record(self, record):
        """ Import a record directly or delay the import of the record """
        raise NotImplementedError


@magento
class SimpleBatchImport(BatchImportSynchronizer):
    """ Import the Magento Websites.

    They are imported directly because this is a rare and fast operation,
    performed from the UI.
    """
    _model_name = [
            'magento.website',
            'magento.store',
            'magento.storeview',
            ]

    def _import_record(self, record):
        """ Import the website record directly """
        magento_id = connector.RecordIdentifier(id=record)
        importer = self.reference.get_class(MagentoImportSynchronizer,
                                            self.environment.model_name)
        importer(self.environment, magento_id).run()


@magento
class WebsiteImport(MagentoImportSynchronizer):
    """ Import one Magento Website """
    _model_name = [
            'magento.website',
            'magento.store',
            'magento.storeview'
        ]
