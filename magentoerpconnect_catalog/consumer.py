# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright 2013
#    Author: Guewen Baconnier - Camptocamp SA
#            Augustin Cisterne-Kaasv - Elico-corp
#            David Béal - Akretion
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
from openerp.addons.connector.event import (on_record_write,
                                            on_record_create,
                                            on_record_unlink
                                            )

import openerp.addons.magentoerpconnect.consumer as magentoerpconnect



@on_record_create(model_names=[
        'magento.product.category',
        'magento.product.product'
    ])
@on_record_write(model_names=[
        'magento.product.category',
        'magento.product.product'
    ])
def delay_export(session, model_name, record_id, fields=None):
    magentoerpconnect.delay_export(session, model_name,
                                   record_id, fields=fields)

@on_record_write(model_names=[
        'product.category',
        'product.product'
    ])
def delay_export_all_bindings(session, model_name, record_id, fields=None):
    magentoerpconnect.delay_export_all_bindings(session, model_name,
                                                record_id, fields=fields)


@on_record_unlink(model_names=[
        'magento.product.category',
        'magento.product.product'
    ])
def delay_unlink(session, model_name, record_id):
    magentoerpconnect.delay_unlink(session, model_name, record_id)
