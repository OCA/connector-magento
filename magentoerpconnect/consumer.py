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

import openerp.addons.connector as connector

from openerp.addons.connector.event import (
    on_record_write,
    on_record_create,
    on_record_unlink
    )
from .queue import job

_MODEL_NAMES = ('res.partner',)
_BIND_MODEL_NAMES = ('magento.res.partner',)


@on_record_create(model_names=_BIND_MODEL_NAMES)
@on_record_write(model_names=_BIND_MODEL_NAMES)
def delay_export(session, model_name, record_id, fields=None):
    if session.context.get('connector_no_export'):
        return
    job.export_record.delay(session, model_name, record_id, fields=fields)


@on_record_write(model_names=_MODEL_NAMES)
def delay_export_all_bindings(session, model_name, record_id, fields=None):
    if session.context.get('connector_no_export'):
        return
    model = session.pool.get(model_name)
    record = model.browse(session.cr, session.uid,
                          record_id, context=session.context)
    for binding in record.magento_bind_ids:
        job.export_record.delay(session, binding._model._name, binding.id,
                                fields=fields)


@on_record_unlink(model_names=_BIND_MODEL_NAMES)
def delay_unlink(session, model_name, record_id):
    model = session.pool.get(model_name)
    record = model.browse(session.cr, session.uid,
                          record_id, context=session.context)
    env = connector.Environment(record.backend_id, session, model_name)
    binder = env.get_connector_unit(connector.Binder)
    magento_id = binder.to_backend(record_id)
    if magento_id:
        job.export_delete_record.delay(session, model_name,
                                       record.backend_id.id, magento_id)
