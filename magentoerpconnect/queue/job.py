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


def _get_environment(session, model_name, backend_id):
    model = session.pool.get('magento.backend')
    backend_record = model.browse(session.cr,
                                  session.uid,
                                  backend_id,
                                  session.context)
    return connector.Environment(backend_record, session, model_name)


@connector.job
def import_batch(session, model_name, backend_id, filters=None):
    """ Prepare a batch import of records from Magento """
    env = _get_environment(session, model_name, backend_id)
    importer = env.get_connector_unit(BatchImportSynchronizer)
    importer.run(filters)


@connector.job
def import_record(session, model_name, backend_id, magento_id):
    """ Import a record from Magento """
    env = _get_environment(session, model_name, backend_id)
    importer = env.get_connector_unit(MagentoImportSynchronizer)
    importer.run(magento_id)


@connector.job
def import_partners_since(session, model_name, backend_id, since_date=None):
    """ Prepare the import of partners modified on Magento """
    env = _get_environment(session, model_name, backend_id)
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


@connector.job
def export_record(session, model_name, openerp_id, fields=None):
    """ Export a record on Magento """
    model = session.pool.get(model_name)
    record = model.browse(session.cr, session.uid, openerp_id,
                          context=session.context)
    env = _get_environment(session, model_name, record.backend_id.id)
    exporter = env.get_connector_unit(MagentoExportSynchronizer)
    return exporter.run(openerp_id, fields=fields)


@connector.job
def export_delete_record(session, model_name, backend_id, magento_id):
    """ Delete a record on Magento """
    env = _get_environment(session, model_name, backend_id)
    deleter = env.get_connector_unit(MagentoDeleteSynchronizer)
    return deleter.run(magento_id)


@connector.job
def export_picking_done(session, model_name, backend_id, record_id, picking_type):
    """
    Launch the job to export the picking with args to ask for partial or complete
    picking.
   
    @params: picking_type as string, can be 'complete' or 'partial'
    """
    env = _get_environment(session, model_name, backend_id)
    picking_exporter = env.get_connector_unit(MagentoPickingSynchronizer)
    res = picking_exporter.run(record_id, picking_type)
    picking_obj = session.pool.get(model_name)
    picking = picking_obj.browse(session.cr, session.uid, record_id, context=session.context)
    if picking.carrier_tracking_ref:
        on_tracking_number_added.fire(session, self._name, record_id, picking.carrier_tracking_ref)
    return res
    
@connector.job
def export_tracking_number(session, model_name, backend_id, record_id, tracking_number):
    """
    Launch the job to export the tracking number.
   
    @param: tracking_number is the carrier tracking number
    @type: string
    """
    env = _get_environment(session, model_name, backend_id)
    tracking_exporter = env.get_connector_unit(MagentoTrackingSynchronizer)
    res = tracking_exporter.run(record_id, tracking_number)
    return res
    
    
    
