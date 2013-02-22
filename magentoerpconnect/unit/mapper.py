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

from openerp.tools.translate import _
import openerp.addons.connector as connector
from openerp.addons.connector import mapping
from ..backend import magento


@magento
class WebsiteImportMapper(connector.ImportMapper):
    _model_name = 'magento.website'

    direct = [('code', 'code')]

    @mapping
    def name(self, record):
        name = record['name']
        if name is None:
            name = _('Undefined')
        return {'name': name}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}


@magento
class StoreImportMapper(connector.ImportMapper):
    _model_name = 'magento.store'

    direct = [('name', 'name')]

    @mapping
    def website_id(self, record):
        binder_cls = self.backend.get_class(connector.Binder, 'magento.website')
        # TODO helper to copy environment with another model
        binder = connector.Environment(
                self.environment.backend_record,
                self.environment.session,
                'magento.website').get_connector_unit(connector.Binder)
        openerp_id = binder.to_openerp(record['website_id'])
        return {'website_id': openerp_id}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}


@magento
class StoreviewImportMapper(connector.ImportMapper):
    _model_name = 'magento.storeview'

    direct = [
        ('name', 'name'),
        ('code', 'code')
    ]

    @mapping
    def store_id(self, record):
        # TODO helper to copy environment with another model
        binder = connector.Environment(
                self.backend_record,
                self.session,
                'magento.store').get_connector_unit(connector.Binder)
        openerp_id = binder.to_openerp(record['group_id'])
        return {'store_id': openerp_id}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}


@magento
class PartnerImportMapper(connector.ImportMapper):
    _model_name = 'res.partner'

    _direct = [('name', 'name')]

    @mapping
    def names(self, record):
        parts = [part for part in(record['firstname'],
                    record['middlename'], record['lastname'])
                    if part]
        return {'name': ' '.join(parts)}


@magento
class PartnerLinkImportMapper(connector.ImportMapper):
    _model_name = 'magento.res.partner'

    _direct = [('created_in', 'created_in')]

    @mapping
    def website_id(self, record):
        binder = connector.Environment(
                self.backend_record,
                self.session,
                'magento.website').get_connector_unit(connector.Binder)
        website_id = binder.to_openerp(record['website_id'])
        return {'website_id': website_id}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}
