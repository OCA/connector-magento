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

from openerp.addons.connector.event import (on_record_write,
                                            on_record_create,
                                            on_record_unlink
                                            )

import openerp.addons.magentoerpconnect.consumer as magentoerpconnect

from openerp.addons.connector.connector import Binder
from openerp.addons.magentoerpconnect.connector import get_environment
from openerp.addons.magentoerpconnect.unit.delete_synchronizer import (
    export_delete_record)


EXCLUDED_FIELDS_WRITING = {
    'product.product': ['magento_bind_ids', 'image_ids'],
    'product.category': ['magento_bind_ids',],
    'magento.product.category': ['magento_bind_ids',],
}

def exclude_fields_from_synchro(model_name, fields):
    if fields and EXCLUDED_FIELDS_WRITING.get(model_name):
        fields = list(set(fields).difference(EXCLUDED_FIELDS_WRITING))
    return fields

@on_record_create(model_names=[
        'magento.product.category',
        'magento.product.product',
        'magento.product.attribute',
        'magento.attribute.set',
        'magento.attribute.option',
        'magento.product.image',
    ])
@on_record_write(model_names=[
        'magento.product.category',
        'magento.product.product',
        'magento.product.attribute',
        'magento.attribute.option',
        'magento.product.image',
        #'magento.product.storeview',
    ])
def delay_export(session, model_name, record_id, vals=None):
    #fields = exclude_fields_from_synchro(model_name, fields)
    magentoerpconnect.delay_export(session, model_name,
                                   record_id, vals=vals)


@on_record_write(model_names=[
        'product.product',
        'product.category',
    ])
def delay_export_all_bindings(session, model_name, record_id, vals=None):
    #fields = exclude_fields_from_synchro(model_name, fields)
    magentoerpconnect.delay_export_all_bindings(session, model_name,
                                                record_id, vals=vals)

#
#@on_record_unlink(model_names=[
#        'product.category',
#    ])
#def delay_unlink_all_bindings(session, model_name, record_id):
#    #magentoerpconnect.delay_unlink_all_bindings(session, model_name, record_id)
#    import pdb;pdb.set_trace()
#    magentoerpconnect.delay_unlink(session, model_name, record_id)


@on_record_unlink(model_names=[
        'magento.product.category',
        'magento.product.product'
        'magento.product.attribute',
        'magento.attribute.set',
        'magento.attribute.option',
    ])
def delay_unlink(session, model_name, record_id):
    magentoerpconnect.delay_unlink(session, model_name, record_id)


@on_record_unlink(model_names=['magento.product.image'])
def delay_image_unlink(session, model_name, record_id):
    model = session.pool.get('magento.product.image')
    record = model.browse(session.cr, session.uid,
                          record_id, context=session.context)
    magento_keys = []
    env = get_environment(session, 'magento.product.image',
                          record.backend_id.id)
    binder = env.get_connector_unit(Binder)
    magento_keys.append(binder.to_backend(record_id))
    # in addition to magento 'image id' needs 'product id' to remove images
    # see http://www.magentocommerce.com/api/soap/catalog/...
    # catalogProductAttributeMedia/catalog_product_attribute_media.remove.html
    env = get_environment(session, 'magento.product.product',
                          record.backend_id.id)
    binder = env.get_connector_unit(Binder)
    magento_keys.append(binder.to_backend(record.openerp_id.product_id.id, wrap=True))
    if magento_keys:
        export_delete_record.delay(session, 'magento.product.image',
                                   record.backend_id.id, magento_keys)
