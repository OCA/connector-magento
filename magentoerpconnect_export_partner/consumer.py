# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.connector.event import (on_record_write,
                                         on_record_create,
                                         on_record_unlink,
                                         )
import odoo.addons.magentoerpconnect.consumer as magentoerpconnect


@on_record_create(model_names=['magento.address', 'magento.res.partner'])
@on_record_write(model_names=['magento.address', 'magento.res.partner'])
def delay_export(env, model_name, record_id, vals):
    magentoerpconnect.delay_export(env, model_name, record_id, vals)


@on_record_write(model_names='res.partner')
def delay_export_all_bindings(env, model_name, record_id, vals):
    magentoerpconnect.delay_export_all_bindings(env, model_name,
                                                record_id, vals)


@on_record_write(model_names='res.partner')
def delay_export_all_bindings_for_address(env, model_name, record_id, vals):
    if env.context.get('connector_no_export'):
        return
    record = env[model_name].browse(record_id)
    for binding in record.magento_address_bind_ids:
        magentoerpconnect.delay_export(env, binding._name,
                                       binding.id, vals)


@on_record_unlink(model_names=['magento.res.partner', 'magento.address'])
def delay_unlink(env, model_name, record_id):
    magentoerpconnect.delay_unlink(env, model_name, record_id)
