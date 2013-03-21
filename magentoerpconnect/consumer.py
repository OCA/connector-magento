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

from openerp.addons.connector.event import (
    on_record_write,
    on_record_create,
    on_record_unlink
    )
from openerp.addons.connector.connector import Environment, Binder

from openerp.addons.connector_ecommerce.event import (on_picking_out_done,
                                                      on_tracking_number_added,
                                                      on_invoice_paid)
from .unit.export_synchronizer import (
    export_record,
    export_picking_done,
    export_tracking_number,
    export_invoice_paid
    )
from .unit.delete_synchronizer import export_delete_record

_MODEL_NAMES = ()
_BIND_MODEL_NAMES = ()


def magento_consumer(func):
    """ Use this decorator on all the consumers of magentoerpconnect.

    It will prevent the consumers from being fired when the magentoerpconnect
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
    binder = env.get_connector_unit(Binder)
    magento_id = binder.to_backend(record_id)
    if magento_id:
        export_delete_record.delay(session, model_name,
                                   record.backend_id.id, magento_id)


@on_picking_out_done
@magento_consumer
def picking_out_done(session, model_name, record_id, picking_method):
    """
    Create a ``magento.stock.picking.out`` record. This record will then
    be exported to Magento.

    :param picking_method: picking_method, can be 'complete' or 'partial'
    :type picking_method: str
    """
    picking = session.browse(model_name, record_id)
    sale = picking.sale_id
    if not sale:
        return
    for magento_sale in sale.magento_bind_ids:
        session.create('magento.stock.picking.out',
                       {'backend_id': magento_sale.backend_id.id,
                        'openerp_id': picking.id,
                        'magento_order_id': magento_sale.id,
                        'picking_method': picking_method})


@on_record_create(model_names='magento.stock.picking.out')
@magento_consumer
def delay_export_picking_out(session, model_name, record_id):
    export_picking_done.delay(session, model_name, record_id)


@on_tracking_number_added
@magento_consumer
def delay_export_tracking_number(session, model_name, record_id):
    """
    Call a job to export the tracking number to a existing picking that
    must be in done state.
    """
    picking = session.browse(model_name, record_id)
    for binding in picking.magento_bind_ids:
        # Set the priority to 20 to have more chance that it would be
        # executed after the picking creation
        export_tracking_number.delay(session,
                                     binding._model._name,
                                     binding.id,
                                     priority=20)


@on_invoice_paid
@magento_consumer
def invoice_paid_create_bindings(session, model_name, record_id):
    """
    Create a ``magento.account.invoice`` record. This record will then
    be exported to Magento.
    """
    invoice = session.browse(model_name, record_id)
    # find the magento store to retrieve the backend
    # we use the shop as many sale orders can be related to an invoice
    for sale in invoice.sale_ids:
        for magento_sale in sale.magento_bind_ids:
            session.create('magento.account.invoice',
                           {'backend_id': magento_sale.backend_id.id,
                            'openerp_id': invoice.id,
                            'magento_order_id': magento_sale.id})


@on_record_create(model_names='magento.account.invoice')
@magento_consumer
def delay_export_account_invoice(session, model_name, record_id):
    """
    Delay the job to export the magento invoice.
    """
    export_invoice_paid.delay(session, model_name, record_id)
