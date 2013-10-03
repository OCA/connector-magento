# -*- coding: utf-8 -*-

from functools import wraps
from openerp.addons.connector.event import (on_record_write,
                                            on_record_create,
                                            on_record_unlink
                                            )
from openerp.addons.magentoerpconnect.unit.export_synchronizer import export_record
import openerp.addons.magentoerpconnect.consumer as magentoerpconnect


@on_record_create(model_names=['magento.product.category', 'magento.product.product'])
@on_record_write(model_names=['magento.product.category', 'magento.product.product'])
def delay_export(session, model_name, record_id, fields=None):
    magentoerpconnect.delay_export(session, model_name,
                                   record_id, fields=fields)

@on_record_write(model_names=['product.category','product.product'])
def delay_export_all_bindings(session, model_name, record_id, fields=None):
    magentoerpconnect.delay_export_all_bindings(session, model_name,
                                                record_id, fields=fields)

@on_record_unlink(model_names=['magento.product.category', 'magento.product.product'])
def delay_unlink(session, model_name, record_id):
	magentoerpconnect.delay_unlink(session, model_name, record_id)
