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

from functools import wraps

import openerp.addons.connector as connector

from openerp.addons.connector.event import (
    on_record_write,
    on_record_create,
    on_record_unlink
    )
from openerp.addons.connector.connector import Environment

from openerp.addons.connector_ecommerce.event import on_picking_done
from .unit.export_synchronizer import export_record, export_picking_done
from .unit.delete_synchronizer import export_delete_record

_MODEL_NAMES = ('res.partner',)
_BIND_MODEL_NAMES = ('magento.res.partner',)


def magento_consumer(func):
    """ Use this decorator on all the consumers of magentoerpconnect.

    It will prevent the consumers to be fired when the magentoerpconnect
    addon is not installed.
    """
    @wraps(func)
    def wrapped(*args, **kwargs):
        session = args[0]
        if session.pool.get('magentoerpconnect.installed'):
            return func(*args, **kwargs)

    return wrapped


@on_record_create(model_names=_BIND_MODEL_NAMES)
@on_record_write(model_names=_BIND_MODEL_NAMES)
@magento_consumer
def delay_export(session, model_name, record_id, fields=None):
    if session.context.get('connector_no_export'):
        return
    export_record.delay(session, model_name, record_id, fields=fields)


@on_record_write(model_names=_MODEL_NAMES)
@magento_consumer
def delay_export_all_bindings(session, model_name, record_id, fields=None):
    if session.context.get('connector_no_export'):
        return
    model = session.pool.get(model_name)
    record = model.browse(session.cr, session.uid,
                          record_id, context=session.context)
    for binding in record.magento_bind_ids:
        export_record.delay(session, binding._model._name, binding.id,
                            fields=fields)


@on_record_unlink(model_names=_BIND_MODEL_NAMES)
@magento_consumer
def delay_unlink(session, model_name, record_id):
    model = session.pool.get(model_name)
    record = model.browse(session.cr, session.uid,
                          record_id, context=session.context)
    env = Environment(record.backend_id, session, model_name)
    binder = env.get_connector_unit(connector.connector.Binder)
    magento_id = binder.to_backend(record_id)
    if magento_id:
        export_delete_record.delay(session, model_name,
                                   record.backend_id.id, magento_id)


@on_picking_done(model_names='stock.picking')
@magento_consumer
def delay_export_picking_done(session, model_name, record_id, picking_type):
    """
    Call a job to export the picking with args to ask for partial or complete
    picking.

    :param picking_type: picking_type, can be 'complete' or 'partial'
    :type picking_type: str
    """
    export_picking_done.delay(session, model_name, record_id, picking_type)
