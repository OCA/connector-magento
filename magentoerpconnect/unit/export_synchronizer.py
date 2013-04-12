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
from openerp.tools.translate import _
from openerp.addons.connector.queue.job import job
from openerp.addons.connector.unit.synchronizer import ExportSynchronizer
from openerp.addons.connector.exception import NothingToDoJob
from ..backend import magento
from ..connector import get_environment

_logger = logging.getLogger(__name__)


class MagentoExportSynchronizer(ExportSynchronizer):
    """ Base exporter for Magento """

    def __init__(self, environment):
        """
        :param environment: current environment (backend, session, ...)
        :type environment: :py:class:`connector.connector.Environment`
        """
        super(MagentoExportSynchronizer, self).__init__(environment)
        self.binding_id = None
        self.openerp_record = None

    def _get_openerp_data(self):
        """ Return the raw OpenERP data for ``self.binding_id`` """
        cr, uid, context = (self.session.cr,
                            self.session.uid,
                            self.session.context)
        return self.model.browse(cr, uid, self.binding_id, context=context)

    def _has_to_skip(self):
        """ Return True if the import can be skipped """
        return False

    def _export_dependencies(self):
        """ Export the dependencies for the record"""
        return

    def _map_data(self, fields=None):
        """ Convert the external record to OpenERP """
        self.mapper.convert(self.openerp_record, fields=fields)

    def _validate_data(self, data):
        """ Check if the values to import are correct

        Pro-actively check before the ``Model.create`` or
        ``Model.update`` if some fields are missing

        Raise `InvalidDataError`
        """
        return

    def _create(self, data):
        """ Create the Magento record """
        magento_id = self.backend_adapter.create(data)
        return magento_id

    def _update(self, magento_id, data):
        """ Update an Magento record """
        self.backend_adapter.write(magento_id, data)

    def run(self, binding_id, fields=None):
        """ Run the synchronization

        :param binding_id: identifier of the record
        """
        self.binding_id = binding_id
        self.openerp_record = self._get_openerp_data()

        magento_id = self.binder.to_backend(self.binding_id)
        if not magento_id:
            fields = None  # should be created with all the fields

        if self._has_to_skip():
            return

        # export the missing linked resources
        self._export_dependencies()

        self._map_data(fields=fields)

        if magento_id:
            record = self.mapper.data
            if not record:
                raise NothingToDoJob
            # special check on data before import
            self._validate_data(record)
            # FIXME magento record could have been deleted,
            # we would need to create the record
            # (with all fields)
            self._update(magento_id, record)
        else:
            record = self.mapper.data_for_create
            if not record:
                raise NothingToDoJob
            # special check on data before import
            self._validate_data(record)
            magento_id = self._create(record)

        self.binder.bind(magento_id, self.binding_id)
        return _('Record exported with ID %s on Magento.') % magento_id


@job
def export_record(session, model_name, binding_id, fields=None):
    """ Export a record on Magento """
    record = session.browse(model_name, binding_id)
    env = get_environment(session, model_name, record.backend_id.id)
    exporter = env.get_connector_unit(MagentoExportSynchronizer)
    return exporter.run(binding_id, fields=fields)
