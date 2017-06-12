# -*- coding: utf-8 -*-
# © 2013 Guewen Baconnier,Camptocamp SA,Akretion
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

# from openerp.addons.connector.connector import Binder
# from .unit.export_synchronizer import export_record
# from .unit.delete_synchronizer import export_delete_record
# from .connector import get_environment


def delay_export(session, model_name, record_id, vals):
    """ Delay a job which export a binding record.

    (A binding record being a ``magento.res.partner``,
    ``magento.product.product``, ...)
    """
    if session.context.get('connector_no_export'):
        return
    fields = vals.keys()
    export_record.delay(session, model_name, record_id, fields=fields)


def delay_export_all_bindings(session, model_name, record_id, vals):
    """ Delay a job which export all the bindings of a record.

    In this case, it is called on records of normal models and will delay
    the export for all the bindings.
    """
    if session.context.get('connector_no_export'):
        return
    record = session.env[model_name].browse(record_id)
    fields = vals.keys()
    for binding in record.magento_bind_ids:
        export_record.delay(session, binding._model._name, binding.id,
                            fields=fields)


def delay_unlink(session, model_name, record_id):
    """ Delay a job which delete a record on Magento.

    Called on binding records."""
    record = session.env[model_name].browse(record_id)
    env = get_environment(session, model_name, record.backend_id.id)
    binder = env.get_connector_unit(Binder)
    external_id = binder.to_backend(record_id)
    if external_id:
        export_delete_record.delay(session, model_name,
                                   record.backend_id.id, external_id)
