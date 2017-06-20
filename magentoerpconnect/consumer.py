# -*- coding: utf-8 -*-
# © 2013 Guewen Baconnier,Camptocamp SA,Akretion
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


def delay_export(env, model_name, record_id, vals):
    """ Delay a job which export a binding record.

    (A binding record being a ``magento.res.partner``,
    ``magento.product.product``, ...)
    """
    if env.context.get('connector_no_export'):
        return
    fields = vals.keys()
    delayable = env[model_name].browse(record_id).with_delay()
    delayable.export_record(fields=fields)


def delay_export_all_bindings(env, model_name, record_id, vals):
    """ Delay a job which export all the bindings of a record.

    In this case, it is called on records of normal models and will delay
    the export for all the bindings.
    """
    if env.context.get('connector_no_export'):
        return
    record = env[model_name].browse(record_id)
    for binding in record.magento_bind_ids:
        delay_export(env, binding._name, binding.id, vals)


def delay_unlink(env, model_name, record_id):
    """ Delay a job which delete a record on Magento.

    Called on binding records."""
    record = env[model_name].browse(record_id)
    with record.backend_id.work_on(model_name) as work:
        binder = work.component(usage='binder')
        external_id = binder.to_external(record_id)
        if external_id:
            binding = env[model_name].browse(record_id)
            binding.with_delay().export_delete_record(record.backend_id,
                                                      external_id)
