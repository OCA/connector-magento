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

import logging
import magento as magentolib
from openerp.osv import fields, orm
from openerp.addons.connector.unit.backend_adapter import BackendAdapter
from openerp.addons.connector.unit.mapper import (mapping,
                                                  ImportMapper
                                                  )
from .unit.backend_adapter import GenericAdapter
from .unit.import_synchronizer import (DelayedBatchImport,
                                       MagentoImportSynchronizer
                                       )
from .backend import magento

_logger = logging.getLogger(__name__)


class res_partner(orm.Model):
    _inherit = 'res.partner'

    _columns = {
        'magento_bind_ids': fields.one2many(
            'magento.res.partner', 'openerp_id',
            string="Magento Bindings"),
        'magento_address_bind_ids': fields.one2many(
            'magento.address', 'openerp_id',
            string="Magento Address Bindings"),
        'birthday': fields.date('Birthday'),
        'company': fields.char('Company'),
    }


# TODO migrate from res.partner (magento fields)
class magento_res_partner(orm.Model):
    _name = 'magento.res.partner'
    _inherit = 'magento.binding'
    _inherits = {'res.partner': 'openerp_id'}

    _rec_name = 'website_id'

    def _get_mag_partner_from_website(self, cr, uid, ids, context=None):
        mag_partner_obj = self.pool['magento.res.partner']
        return mag_partner_obj.search(cr, uid,
                                [('website_id', 'in', ids)],
                                context=context)

    _columns = {
        'openerp_id': fields.many2one('res.partner',
                                      string='Partner',
                                      required=True,
                                      ondelete='cascade'),
        'backend_id': fields.related('website_id', 'backend_id',
                                     type='many2one',
                                     relation='magento.backend',
                                     string='Magento Backend',
                                     store={
                                        'magento.res.partner':
                                        (lambda self, cr, uid, ids, c=None: ids,
                                         ['website_id'],
                                         10),
                                        'magento.website':
                                        (_get_mag_partner_from_website,
                                         ['backend_id'],
                                         20),
                                        },
                                     readonly=True),
        'website_id': fields.many2one('magento.website',
                                      string='Magento Website',
                                      required=True,
                                      ondelete='restrict'),
        'group_id': fields.many2one('magento.res.partner.category',
                                    string='Magento Group (Category)'),
        'created_at': fields.datetime('Created At (on Magento)',
                                      readonly=True),
        'updated_at': fields.datetime('Updated At (on Magento)',
                                      readonly=True),
        'emailid': fields.char('E-mail address'),
        'taxvat': fields.char('Magento VAT'),
        'newsletter': fields.boolean('Newsletter'),
        'guest_customer': fields.boolean('Guest Customer'),
    }

    _sql_constraints = [
        ('magento_uniq', 'unique(website_id, magento_id)',
         'A partner with same ID on Magento already exists for this website.'),
    ]


class magento_address(orm.Model):
    _name = 'magento.address'
    _inherit = 'magento.binding'
    _inherits = {'res.partner': 'openerp_id'}

    _rec_name = 'backend_id'

    def _get_mag_address_from_partner(self, cr, uid, ids, context=None):
        mag_address_obj = self.pool['magento.address']
        return mag_address_obj.search(cr, uid,
                                [('magento_partner_id', 'in', ids)],
                                context=context)

    _columns = {
        'openerp_id': fields.many2one('res.partner',
                                      string='Partner',
                                      required=True,
                                      ondelete='cascade'),
        'created_at': fields.datetime('Created At (on Magento)',
                                      readonly=True),
        'updated_at': fields.datetime('Updated At (on Magento)',
                                      readonly=True),
        'is_default_billing': fields.boolean('Default Invoice'),
        'is_default_shipping': fields.boolean('Default Shipping'),
        'magento_partner_id': fields.many2one('magento.res.partner',
                                              string='Magento Partner',
                                              required=True,
                                              ondelete='cascade'),
        'backend_id': fields.related('magento_partner_id', 'backend_id',
                                     type='many2one',
                                     relation='magento.backend',
                                     string='Magento Backend',
                                     store={
                                        'magento.address':
                                        (lambda self, cr, uid, ids, c=None: ids,
                                         ['magento_partner_id'],
                                         10),
                                        'magento.res.partner':
                                        (_get_mag_address_from_partner,
                                         ['backend_id', 'website_id'],
                                         20),
                                        },
                                     readonly=True),
        'website_id': fields.related('magento_partner_id', 'website_id',
                                     type='many2one',
                                     relation='magento.website',
                                     string='Magento Website',
                                     store={
                                        'magento.address':
                                        (lambda self, cr, uid, ids, c=None: ids,
                                         ['magento_partner_id'],
                                         10),
                                        'magento.res.partner':
                                        (_get_mag_address_from_partner,
                                         ['website_id'],
                                         20),
                                        },
                                     readonly=True),
        'is_magento_order_address': fields.boolean('Address from a Magento Order'),
    }

    _sql_constraints = [
        ('magento_uniq', 'unique(backend_id, magento_id)',
         'A partner address with same ID on Magento already exists.'),
    ]


@magento
class PartnerAdapter(GenericAdapter):
    _model_name = 'magento.res.partner'
    _magento_model = 'customer'

    def search(self, filters=None, from_date=None, magento_website_ids=None):
        """ Search records according to some criterias and returns a
        list of ids

        :rtype: list
        """
        if filters is None:
            filters = {}

        if from_date is not None:
            # updated_at include the created records
            filters['updated_at'] = {'from': from_date.strftime('%Y/%m/%d %H:%M:%S')}
        if magento_website_ids is not None:
            filters['website_id'] = {'in': magento_website_ids}

        with magentolib.API(self.magento.location,
                            self.magento.username,
                            self.magento.password) as api:
            # the search method is on ol_customer instead of customer
            return api.call('ol_customer.search',
                            [filters] if filters else [{}])
        return []


@magento
class PartnerBatchImport(DelayedBatchImport):
    """ Import the Magento Partners.

    For every partner in the list, a delayed job is created.
    """
    _model_name = ['magento.res.partner']

    def run(self, filters=None):
        """ Run the synchronization """
        from_date = filters.pop('from_date', None)
        magento_website_ids = [filters.pop('magento_website_id')]
        record_ids = self.backend_adapter.search(filters,
                                                 from_date,
                                                 magento_website_ids)
        _logger.info('search for magento partners %s returned %s',
                     filters, record_ids)
        for record_id in record_ids:
            self._import_record(record_id)


@magento
class PartnerImport(MagentoImportSynchronizer):
    _model_name = ['magento.res.partner']

    def _import_dependencies(self):
        """ Import the dependencies for the record"""
        record = self.magento_record

        # import customer groups
        binder = self.get_binder_for_model('magento.res.partner.category')
        if binder.to_openerp(record['group_id']) is None:
            importer = self.get_connector_unit_for_model(MagentoImportSynchronizer,
                                                         'magento.res.partner.category')
            importer.run(record['group_id'])

    def _after_import(self, magento_res_partner_openerp_id):
        """ Import the addresses """
        addresses_adapter = self.get_connector_unit_for_model(BackendAdapter,
                                                              'magento.address')
        mag_address_ids = addresses_adapter.search(
                {'customer_id': {'eq': self.magento_id}})
        if not mag_address_ids:
            return
        importer = self.get_connector_unit_for_model(MagentoImportSynchronizer,
                                                     'magento.address')
        partner_row = self.model.read(self.session.cr,
                                      self.session.uid,
                                      magento_res_partner_openerp_id,
                                      ['openerp_id'],
                                      context=self.session.context)
        res_partner_openerp_id = partner_row['openerp_id'][0]
        mag_addresses = {} # mag_address_id -> True if address is linked to existing partner,
                           #                   False otherwise
        if len(mag_address_ids) == 1:
            mag_addresses[mag_address_ids[0]] = True
        else:
            billing_address = False
            for address_id in mag_address_ids:
                magento_record = addresses_adapter.read(address_id)

                if magento_record['is_default_billing']:
                    mag_addresses[address_id] = True
                    billing_address = True
                else:
                    mag_addresses[address_id] = False
            if not billing_address:
                mag_addresses[min(mag_addresses)] = True
        for address_id, to_link in mag_addresses.iteritems():
            importer.run(address_id,
                         magento_res_partner_openerp_id,
                         res_partner_openerp_id,
                         to_link)


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
        category_id = binder.to_openerp(record['group_id'], unwrap=True)

        if category_id is None:
            raise MappingError("The partner category with "
                               "magento id %s does not exist" %
                               record['group_id'])

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

    @mapping
    def lang(self, record):
        binder = self.get_binder_for_model('magento.storeview')
        openerp_id = binder.to_openerp(record['store_id'])
        lang = False
        if openerp_id:
            storeview = self.session.browse('magento.storeview',
                                            openerp_id)
            lang = storeview.lang_id and storeview.lang_id.code
        return {'lang': lang}


@magento
class AddressAdapter(GenericAdapter):
    _model_name = 'magento.address'
    _magento_model = 'customer_address'

    def search(self, filters=None):
        """ Search records according to some criterias
        and returns a list of ids

        :rtype: list
        """
        with magentolib.API(self.magento.location,
                            self.magento.username,
                            self.magento.password) as api:
            return [int(row['customer_address_id']) for row
                       in api.call('%s.list' % self._magento_model,
                                   [filters] if filters else [{}])]
        return []


@magento
class AddressImport(MagentoImportSynchronizer):
    _model_name = ['magento.address']

    def run(self, magento_id, magento_partner_id, partner_id, link_with_partner):
        """ Run the synchronization """
        self.partner_id = partner_id
        self.magento_partner_id = magento_partner_id
        self.link_with_partner = link_with_partner
        super(AddressImport, self).run(magento_id)

    def _map_data(self):
        """ Return the external record converted to OpenERP """
        data = super(AddressImport, self)._map_data()
        if self.link_with_partner:
            data['openerp_id'] = self.partner_id
        else:
            data['parent_id'] = self.partner_id
            partner = self.session.browse('res.partner',
                                          self.partner_id)
            data['lang'] = partner.lang
        data['magento_partner_id'] = self.magento_partner_id
        return data


@magento
class AddressImportMapper(ImportMapper):
    _model_name = 'magento.address'

# TODO fields not mapped:
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
            ('company', 'company'),
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
        lines = [line.strip() for line in value.split('\n') if line.strip()]
        if len(lines) == 1:
            result = {'street': lines[0], 'street2': False}
        elif len(lines) >= 2:
            result = {'street': lines[0], 'street2': u' - '.join(lines[1:])}
        else:
            result = {}
        return result

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}

    @mapping
    def use_parent_address(self, record):
        return {'use_parent_address': False}

    @mapping
    def type(self, record):
        #TODO select type from sale order datas
        if record.get('is_default_shipping'):
            address_type = 'delivery'
        else:
            address_type = 'default'
        return {'type': address_type}

    @mapping
    def title(self, record):
        prefix = record['prefix']
        title_id = False
        if prefix:
            title_ids = self.session.search('res.partner.title',
                                            [('domain', '=', 'contact'),
                                            ('shortcut', 'ilike', prefix)])
            if title_ids:
                title_id = title_ids[0]
            else:
                title_id = self.session.create('res.partner.title',
                                               {'domain': 'contact',
                                               'shortcut': prefix,
                                               'name' : prefix})
        return {'title': title_id}
