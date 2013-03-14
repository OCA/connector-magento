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
from openerp.addons.connector.unit.mapper import (mapping,
                                                  changed_by,
                                                  ImportMapper,
                                                  ExportMapper)
from ..backend import magento


@magento
class WebsiteImportMapper(ImportMapper):
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
class StoreImportMapper(ImportMapper):
    _model_name = 'magento.store'

    direct = [('name', 'name')]

    @mapping
    def website_id(self, record):
        binder = self.get_binder_for_model('magento.website')
        openerp_id = binder.to_openerp(record['website_id'])
        return {'website_id': openerp_id}


@magento
class StoreviewImportMapper(ImportMapper):
    _model_name = 'magento.storeview'

    direct = [
        ('name', 'name'),
        ('code', 'code')
    ]

    @mapping
    def store_id(self, record):
        binder = self.get_binder_for_model('magento.store')
        openerp_id = binder.to_openerp(record['group_id'])
        return {'store_id': openerp_id}


@magento
class PartnerImportMapper(ImportMapper):
    _model_name = 'magento.res.partner'

    direct = [
            ('email', 'email'),
            ('dob', 'birthday'),
            ('created_at', 'created_at'),
            ('updated_at', 'updated_at'),
            ('email', 'emailid'),
            ('taxvat', 'taxvat'),
            ('group_id', 'group_id'),
        ]

    @mapping
    def is_company(self, record):
        # partners are companies so we can bind
        # addresses on them
        return {'is_company': True}

    @mapping
    def names(self, record):
        # TODO create a glue module for base_surname
        parts = [part for part in(record['firstname'],
                    record['middlename'], record['lastname'])
                    if part]
        return {'name': ' '.join(parts)}

    @mapping
    def customer_group_id(self, record):
        # import customer groups
        binder = self.get_binder_for_model('magento.res.partner.category')
        mag_cat_id = binder.to_openerp(record['group_id'])

        if mag_cat_id is None:
            raise connector.exception.MappingError(
                    "The partner category with "
                    "magento id %s does not exist" %
                    record['group_id'])

        category_id = self.session.read('magento.res.partner.category',
                                        mag_cat_id,
                                        ['openerp_id'])['openerp_id'][0]

        # FIXME: should remove the previous tag (all the other tags from
        # the same backend)
        return {'category_id': [(4, category_id)]}

    @mapping
    def website_id(self, record):
        binder = self.get_binder_for_model('magento.website')
        website_id = binder.to_openerp(record['website_id'])
        return {'website_id': website_id}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}


@magento
class PartnerExportMapper(ExportMapper):
    _model_name = 'magento.res.partner'

    direct = [
            ('emailid', 'email'),
            ('birthday', 'dob'),
            ('created_at', 'created_at'),
            ('updated_at', 'updated_at'),
            ('emailid', 'email'),
            ('taxvat', 'taxvat'),
            ('group_id', 'group_id'),
            ('website_id', 'website_id'),
        ]

    @changed_by('name')
    @mapping
    def names(self, record):
        # FIXME base_surname needed
        if ' ' in record.name:
            parts = record.name.split()
            firstname = parts[0]
            lastname = ' '.join(parts[1:])
        else:
            lastname = record.name
            firstname = '-'
        return {'firstname': firstname, 'lastname': lastname}


@magento
class PartnerCategoryImportMapper(ImportMapper):
    _model_name = 'magento.res.partner.category'

    direct = [
            ('customer_group_code', 'name'),
            ('tax_class_id', 'tax_class_id'),
            ]

    @mapping
    def magento_id(self, record):
        return {'magento_id': record['customer_group_id']}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}


@magento
class AddressImportMapper(ImportMapper):
    _model_name = 'magento.address'

# TODO fields not mapped:
#   "company"=>"a",
#   "prefix"=>"a",
#   "suffix"=>"a",
#   "vat_id"=>"12334",

    direct = [
            ('postcode', 'zip'),
            ('city', 'city'),
            ('created_at', 'created_at'),
            ('updated_at', 'updated_at'),
            ('telephone', 'phone'),
            ('fax', 'fax'),
            ('is_default_billing', 'is_default_billing'),
            ('is_default_shipping', 'is_default_shipping'),
        ]

    @mapping
    def names(self, record):
        # TODO create a glue module for base_surname
        parts = [part for part in(record['firstname'],
                    record.get('middlename'), record['lastname'])
                    if part]
        return {'name': ' '.join(parts)}

    @mapping
    def state(self, record):
        if not record.get('state'):
            return
        state_ids = self.session.search('res.country.state',
                                        [('name', 'ilike', record['state'])])
        if state_ids:
            return {'state_id': state_ids[0]}

    @mapping
    def country(self, record):
        if not record.get('country_id'):
            return
        country_ids = self.session.search('res.country',
                                          [('code', '=', record['country_id'])])
        if country_ids:
            return {'country_id': country_ids[0]}

    @mapping
    def street(self, record):
        value = record['street']
        if not value:
            return
        parts = value.split('\n')
        if len(parts) == 2:
            result = {'street': parts[0],
                      'street2': parts[1]}
        else:
            result = {'street': value.replace('\\n', ',')}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}


@magento
class ProductCategoryImportMapper(ImportMapper):
    _model_name = 'magento.product.category'

    direct = [
            ('description', 'description'),
            ]

    @mapping
    def name(self, record):
        return {'name': record['name'] or _('Undefined')}

    @mapping
    def magento_id(self, record):
        return {'magento_id': record['category_id']}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}

    @mapping
    def parent_id(self, record):
        if not record.get('parent_id'):
            return
        binder = self.get_binder_for_model()
        mag_cat_id = binder.to_openerp(record['parent_id'])

        if mag_cat_id is None:
            raise connector.exception.MappingError(
                    "The product category with "
                    "magento id %s does not exist" %
                    record['parent_id'])
        category_id = self.session.read(self.model._name,
                                        mag_cat_id,
                                        ['openerp_id'])['openerp_id'][0]

        return {'parent_id': category_id, 'magento_parent_id': mag_cat_id}


@magento
class ProductImportMapper(ImportMapper):
    _model_name = 'magento.product.product'
    #TODO :     categ, special_price => minimal_price
    direct = [
            ('name', 'name'),
            ('description', 'description'),
            ('weight', 'weight'),
            ('price', 'list_price'),
            ('cost', 'standard_price'),
            ('short_description', 'description_sale'),
            ('sku', 'default_code'),
            ('type_id', 'product_type'),
            ]

    @mapping
    def type(self, record):
        if record['type_id'] == 'simple':
            return {'type': 'product'}
        return

    @mapping
    def website_ids(self, record):
        website_ids = []
        for mag_website_id in record['websites']:
            binder = self.get_binder_for_model('magento.website')
            website_id = binder.to_openerp(mag_website_id)
            website_ids.append(website_id)
        return {'website_ids': website_ids}

    @mapping
    def magento_id(self, record):
        return {'magento_id': record['product_id']}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}
