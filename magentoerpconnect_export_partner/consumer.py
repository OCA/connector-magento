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

from openerp.addons.connector.event import (on_record_write,
                                            on_record_create,
                                            on_record_unlink
                                            )
import openerp.addons.magentoerpconnect.consumer as magentoerpconnect


@on_record_create(model_names=['magento.address', 'magento.res.partner'])
@on_record_write(model_names=['magento.address', 'magento.res.partner'])
def delay_export(session, model_name, record_id, vals):
    magentoerpconnect.delay_export(session, model_name,
                                   record_id, vals)


@on_record_write(model_names='res.partner')
def delay_export_all_bindings(session, model_name, record_id, vals):
    magentoerpconnect.delay_export_all_bindings(session, model_name,
                                                record_id, vals)


@on_record_write(model_names='res.partner')
def delay_export_all_bindings_for_address(session, model_name,
                                          record_id, vals):
    if session.context.get('connector_no_export'):
        return
    record = session.browse(model_name, record_id)
    for binding in record.magento_address_bind_ids:
        magentoerpconnect.delay_export(session, binding._model._name,
                                       binding.id, vals)


@on_record_unlink(model_names=['magento.res.partner', 'magento.address'])
def delay_unlink(session, model_name, record_id):
    magentoerpconnect.delay_unlink(session, model_name, record_id)
