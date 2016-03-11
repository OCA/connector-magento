# -*- coding: utf-8 -*-
#
#    Author: Damien Crier
#    Copyright 2015 Camptocamp SA
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
from openerp.addons.connector.event import (on_record_write,
                                            on_record_create,
                                            on_record_unlink
                                            )

import openerp.addons.magentoerpconnect.consumer as magentoerpconnect

EXCLUDED_FIELDS_WRITING = {
    'product.product': ['magento_bind_ids', 'image_ids'],
    'product.category': ['magento_bind_ids'],
    'magento.product.category': ['magento_bind_ids'],
}


def exclude_fields_from_synchro(model_name, fields):
    if fields and EXCLUDED_FIELDS_WRITING.get(model_name):
        fields = list(set(fields).difference(EXCLUDED_FIELDS_WRITING))
    return fields


@on_record_create(model_names=[
    'magento.product.product',
    ])
@on_record_write(model_names=[
    'magento.product.product',
    ])
def delay_export(session, model_name, record_id, vals=None):
    magentoerpconnect.delay_export(session, model_name,
                                   record_id, vals=vals)


@on_record_write(model_names=[
    'product.product',
    'product.category',
    ])
def delay_export_all_bindings(session, model_name, record_id, vals=None):
    magentoerpconnect.delay_export_all_bindings(session, model_name,
                                                record_id, vals=vals)


@on_record_unlink(model_names=[
    'magento.product.product',
    ])
def delay_unlink(session, model_name, record_id):
    magentoerpconnect.delay_unlink(session, model_name, record_id)
