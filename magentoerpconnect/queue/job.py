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

from datetime import datetime

import openerp.addons.connector as connector
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from ..unit.import_synchronizer import (
        BatchImportSynchronizer,
        MagentoImportSynchronizer)
from ..unit.export_synchronizer import (
        MagentoExportSynchronizer)
from ..unit.delete_synchronizer import (
        MagentoDeleteSynchronizer)


def _get_environment(session, backend_id, model_name):
    model = session.pool.get('magento.backend')
    backend_record = model.browse(session.cr,
                                  session.uid,
                                  backend_id,
                                  session.context)
    return connector.Environment(backend_record, session, model_name)


@connector.job
def import_batch(session, backend_id, model_name, filters=None):
    """ Prepare an batch import of records from Magento """
    env = _get_environment(session, backend_id, model_name)
    importer = env.get_connector_unit(BatchImportSynchronizer)
    importer.run(filters)


@connector.job
def import_record(session, backend_id, model_name, magento_id):
    """ Import a record from Magento """
    env = _get_environment(session, backend_id, model_name)
    importer = env.get_connector_unit(MagentoImportSynchronizer)
    importer.run(magento_id)


@connector.job
def import_partners_since(session, backend_id, since_date=None):
    """ Prepare the import of partners modified on Magento """
    env = _get_environment(session, backend_id, 'magento.res.partner')
    importer = env.get_connector_unit(BatchImportSynchronizer)
    now_fmt = datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
    importer.run(since=since_date)
    session.pool.get('magento.backend').write(
            session.cr,
            session.uid,
            backend_id,
            {'import_partners_since': now_fmt},
            context=session.context)


@connector.job
def export_record(session, model_name, openerp_id, fields=None):
    """ Export a record on Magento """
    model = session.pool.get(model_name)
    record = model.browse(session.cr, session.uid, openerp_id,
                          context=session.context)
    env = _get_environment(session, record.backend_id.id, model_name)
    exporter = env.get_connector_unit(MagentoExportSynchronizer)
    return exporter.run(openerp_id, fields=fields)


@connector.job
def export_delete_record(session, backend_id, model_name, magento_id):
    """ Delete a record on Magento """
    env = _get_environment(session, backend_id, model_name)
    deleter = env.get_connector_unit(MagentoDeleteSynchronizer)
    return deleter.run(magento_id)
