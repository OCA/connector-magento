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
import xmlrpclib
from collections import namedtuple
from openerp.osv import fields, orm
from openerp.addons.connector.queue.job import job
from openerp.addons.connector.connector import ConnectorUnit
from openerp.addons.connector.exception import MappingError
from openerp.addons.connector.unit.backend_adapter import BackendAdapter
from openerp.addons.connector.unit.mapper import (mapping,
                                                  only_create,
                                                  ImportMapper
                                                  )
from openerp.addons.connector.exception import IDMissingInBackend
from .unit.backend_adapter import (GenericAdapter,
                                   MAGENTO_DATETIME_FORMAT,
                                   )
from .unit.import_synchronizer import (DelayedBatchImport,
                                       MagentoImportSynchronizer
                                       )
from .backend import magento
from .connector import get_environment

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

    def copy_data(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default['magento_bind_ids'] = False
        return super(res_partner, self).copy_data(cr, uid, id,
                                                  default=default,
                                                  context=context)

    def _address_fields(self, cr, uid, context=None):
        """ Returns the list of address fields that are synced from the parent
        when the `use_parent_address` flag is set. """
        fields = super(res_partner, self)._address_fields(cr, uid,
                                                          context=context)
        fields.append('company')
        return fields


class magento_res_partner(orm.Model):
    _name = 'magento.res.partner'
    _inherit = 'magento.binding'
    _inherits = {'res.partner': 'openerp_id'}
    _description = 'Magento Partner'

    _rec_name = 'name'

    def _get_mag_partner_from_website(self, cr, uid, ids, context=None):
        mag_partner_obj = self.pool['magento.res.partner']
        return mag_partner_obj.search(
            cr, uid, [('website_id', 'in', ids)], context=context)

    _columns = {
        'openerp_id': fields.many2one('res.partner',
                                      string='Partner',
                                      required=True,
                                      ondelete='cascade'),
        'backend_id': fields.related(
            'website_id', 'backend_id',
            type='many2one',
            relation='magento.backend',
            string='Magento Backend',
            store={
                'magento.res.partner': (lambda self, cr, uid, ids, c=None: ids,
                                        ['website_id'], 10),
                'magento.website': (_get_mag_partner_from_website,
                                    ['backend_id'], 20),
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
        'consider_as_company': fields.boolean(
            'Considered as company',
            help="An account imported with a 'company' in "
                 "the billing address is considered as a company.\n "
                 "The partner takes the name of the company and "
                 "is not merged with the billing address."),
    }

    _sql_constraints = [
        ('magento_uniq', 'unique(website_id, magento_id)',
         'A partner with same ID on Magento already exists for this website.'),
    ]


class magento_address(orm.Model):
    _name = 'magento.address'
    _inherit = 'magento.binding'
    _inherits = {'res.partner': 'openerp_id'}
    _description = 'Magento Address'

    _rec_name = 'backend_id'

    def _get_mag_address_from_partner(self, cr, uid, ids, context=None):
        mag_address_obj = self.pool['magento.address']
        return mag_address_obj.search(
            cr, uid, [('magento_partner_id', 'in', ids)], context=context)

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
        'backend_id': fields.related(
            'magento_partner_id', 'backend_id',
            type='many2one',
            relation='magento.backend',
            string='Magento Backend',
            store={
                'magento.address': (lambda self, cr, uid, ids, c=None: ids,
                                    ['magento_partner_id'], 10),
                'magento.res.partner': (_get_mag_address_from_partner,
                                        ['backend_id', 'website_id'], 20),
            },
            readonly=True),
        'website_id': fields.related(
            'magento_partner_id', 'website_id',
            type='many2one',
            relation='magento.website',
            string='Magento Website',
            store={
                'magento.address': (lambda self, cr, uid, ids, c=None: ids,
                                    ['magento_partner_id'], 10),
                'magento.res.partner': (_get_mag_address_from_partner,
                                        ['website_id'], 20),
            },
            readonly=True),
        'is_magento_order_address': fields.boolean(
            'Address from a Magento Order'),
    }

    _sql_constraints = [
        ('magento_uniq', 'unique(backend_id, magento_id)',
         'A partner address with same ID on Magento already exists.'),
        ('openerp_uniq', 'unique(backend_id, openerp_id)',
         'A partner address can only have one binding by backend.'),
    ]


@magento
class PartnerAdapter(GenericAdapter):
    _model_name = 'magento.res.partner'
    _magento_model = 'customer'
    _admin_path = '/{model}/edit/id/{id}'

    def _call(self, method, arguments):
        try:
            return super(PartnerAdapter, self)._call(method, arguments)
        except xmlrpclib.Fault as err:
            # this is the error in the Magento API
            # when the customer does not exist
            if err.faultCode == 102:
                raise IDMissingInBackend
            else:
                raise

    def search(self, filters=None, from_date=None, to_date=None,
               magento_website_ids=None):
        """ Search records according to some criteria and return a
        list of ids

        :rtype: list
        """
        if filters is None:
            filters = {}

        dt_fmt = MAGENTO_DATETIME_FORMAT
        if from_date is not None:
            # updated_at include the created records
            filters.setdefault('updated_at', {})
            filters['updated_at']['from'] = from_date.strftime(dt_fmt)
        if to_date is not None:
            filters.setdefault('updated_at', {})
            filters['updated_at']['to'] = to_date.strftime(dt_fmt)
        if magento_website_ids is not None:
            filters['website_id'] = {'in': magento_website_ids}

        # the search method is on ol_customer instead of customer
        return self._call('ol_customer.search',
                          [filters] if filters else [{}])


@magento
class PartnerBatchImport(DelayedBatchImport):
    """ Import the Magento Partners.

    For every partner in the list, a delayed job is created.
    """
    _model_name = ['magento.res.partner']

    def run(self, filters=None):
        """ Run the synchronization """
        from_date = filters.pop('from_date', None)
        to_date = filters.pop('to_date', None)
        magento_website_ids = [filters.pop('magento_website_id')]
        record_ids = self.backend_adapter.search(
            filters,
            from_date=from_date,
            to_date=to_date,
            magento_website_ids=magento_website_ids)
        _logger.info('search for magento partners %s returned %s',
                     filters, record_ids)
        for record_id in record_ids:
            self._import_record(record_id)


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

    @only_create
    @mapping
    def is_company(self, record):
        # partners are companies so we can bind
        # addresses on them
        return {'is_company': True}

    @mapping
    def names(self, record):
        # TODO create a glue module for base_surname
        parts = [part for part in (record['firstname'],
                                   record['middlename'],
                                   record['lastname']) if part]
        return {'name': ' '.join(parts)}

    @mapping
    def customer_group_id(self, record):
        # import customer groups
        binder = self.binder_for('magento.res.partner.category')
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
        binder = self.binder_for('magento.website')
        website_id = binder.to_openerp(record['website_id'])
        return {'website_id': website_id}

    @only_create
    @mapping
    def company_id(self, record):
        binder = self.binder_for('magento.storeview')
        storeview = binder.to_openerp(record['store_id'], browse=True)
        if storeview:
            company = storeview.backend_id.company_id
            if company:
                return {'company_id': company.id}
        return {'company_id': False}

    @mapping
    def lang(self, record):
        binder = self.binder_for('magento.storeview')
        storeview = binder.to_openerp(record['store_id'], browse=True)
        if storeview:
            if storeview.lang_id:
                return {'lang': storeview.lang_id.code}

    @only_create
    @mapping
    def customer(self, record):
        return {'customer': True}

    @mapping
    def type(self, record):
        return {'type': 'default'}

    @only_create
    @mapping
    def openerp_id(self, record):
        """ Will bind the customer on a existing partner
        with the same email """
        partner = self.records('res.partner').search(
            [('email', '=', record['email']),
             ('customer', '=', True),
             '|',
             ('is_company', '=', True),
             ('parent_id', '=', False)],
            limit=1,
        )
        if partner:
            return {'openerp_id': partner.id}


@magento
class PartnerImport(MagentoImportSynchronizer):
    _model_name = ['magento.res.partner']

    _base_mapper = PartnerImportMapper

    def _import_dependencies(self):
        """ Import the dependencies for the record"""
        record = self.magento_record
        self._import_dependency(record['group_id'],
                                'magento.res.partner.category')

    def _after_import(self, partner_binding):
        """ Import the addresses """
        book = self.unit_for(PartnerAddressBook, model='magento.address')
        book.import_addresses(self.magento_id, partner_binding.id)


AddressInfos = namedtuple('AddressInfos', ['magento_record',
                                           'partner_binding_id',
                                           'merge'])


@magento
class PartnerAddressBook(ConnectorUnit):
    """ Import all addresses from the address book of a customer.

        This class is responsible to define which addresses should
        be imported and how (merge with the partner or not...).
        Then, it delegate the import to the appropriate importer.

        This is really intricate. The datamodel are different between
        Magento and OpenERP and we have many uses cases to cover.

        The first thing is that:
            - we do not import companies and individuals the same manner
            - we do not know if an account is a company -> we assume that
              if we found something in the company field of the billing
              address, the whole account is a company.

        Differences:
            - Individuals: we merge the billing address with the partner,
              so we'll end with 1 entity if the customer has 1 address
            - Companies: we never merge the addresses with the partner,
              but we use the company name of the billing address as name
              of the partner. We also copy the address informations from
              the billing address as default values.

        More information on:
        https://bugs.launchpad.net/openerp-connector/+bug/1193281
    """
    _model_name = 'magento.address'

    def import_addresses(self, magento_partner_id, partner_binding_id):
        addresses = self._get_address_infos(magento_partner_id,
                                            partner_binding_id)
        for address_id, infos in addresses:
            importer = self.unit_for(MagentoImportSynchronizer)
            importer.run(address_id, infos)

    def _get_address_infos(self, magento_partner_id, partner_binding_id):
        adapter = self.unit_for(BackendAdapter)
        mag_address_ids = adapter.search({'customer_id':
                                          {'eq': magento_partner_id}})
        if not mag_address_ids:
            return
        for address_id in mag_address_ids:
            magento_record = adapter.read(address_id)

            # defines if the billing address is merged with the partner
            # or imported as a standalone contact
            merge = False
            if magento_record.get('is_default_billing'):
                binding_model = self.records('magento.res.partner')
                partner_binding = binding_model.browse(partner_binding_id)
                if magento_record.get('company'):
                    # when a company is there, we never merge the contact
                    # with the partner.
                    # Copy the billing address on the company
                    # and use the name of the company for the name
                    company_mapper = self.unit_for(CompanyImportMapper,
                                                   model='magento.res.partner')
                    map_record = company_mapper.map_record(magento_record)
                    partner_binding.write(map_record.values())
                else:
                    # for B2C individual customers, merge with the main
                    # partner
                    merge = True
                    # in the case if the billing address no longer
                    # has a company, reset the flag
                    partner_binding.write({'consider_as_company': False})
            address_infos = AddressInfos(magento_record=magento_record,
                                         partner_binding_id=partner_binding_id,
                                         merge=merge)
            yield address_id, address_infos


class BaseAddressImportMapper(ImportMapper):
    """ Defines the base mappings for the imports
    in ``res.partner`` (state, country, ...)
    """
    direct = [('postcode', 'zip'),
              ('city', 'city'),
              ('telephone', 'phone'),
              ('fax', 'fax'),
              ('company', 'company'),
              ]

    @mapping
    def state(self, record):
        if not record.get('region'):
            return
        state = self.records('res.country.state').search(
            [('name', '=ilike', record['region'])],
            limit=1,
        )
        if state:
            return {'state_id': state.id}

    @mapping
    def country(self, record):
        if not record.get('country_id'):
            return
        country = self.records('res.country').search(
            [('code', '=', record['country_id'])],
            limit=1
        )
        if country:
            return {'country_id': country.id}

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
    def title(self, record):
        prefix = record['prefix']
        if not prefix:
            return
        title = self.records('res.partner.title').search(
            [('domain', '=', 'contact'),
             ('shortcut', '=ilike', prefix)],
            limit=1
        )
        if not title:
            title = self.records('res.partner.title').create(
                {'domain': 'contact',
                 'shortcut': prefix,
                 'name': prefix,
                 }
            )
        return {'title': title.id}

    @only_create
    @mapping
    def company_id(self, record):
        parent_id = record.get('parent_id')
        if parent_id:
            parent = self.records('res.partner').browse(parent_id)
            if parent.company_id:
                return {'company_id': parent.company_id.id}
            else:
                return {'company_id': False}
        # Don't return anything, we are merging into an existing partner
        return


@magento
class CompanyImportMapper(BaseAddressImportMapper):
    """ Special mapping used when we import a company.
    A company is considered as such when the billing address
    of an account has something in the 'company' field.

    This is a very special mapping not used in the same way
    than the other.

    The billing address will exist as a contact,
    but we want to *copy* the data on the company.

    The input record is the billing address.
    The mapper returns data which will be written on the
    main partner, in other words, the company.

    The ``@only_create`` decorator would not have any
    effect here because the mapper is always called
    for updates.
    """
    _model_name = 'magento.res.partner'

    direct = BaseAddressImportMapper.direct + [
        ('company', 'name'),
    ]

    @mapping
    def consider_as_company(self, record):
        return {'consider_as_company': True}


@magento
class AddressAdapter(GenericAdapter):
    _model_name = 'magento.address'
    _magento_model = 'customer_address'

    def search(self, filters=None):
        """ Search records according to some criterias
        and returns a list of ids

        :rtype: list
        """
        return [int(row['customer_address_id']) for row
                in self._call('%s.list' % self._magento_model,
                              [filters] if filters else [{}])]

    def create(self, customer_id, data):
        """ Create a record on the external system """
        return self._call('%s.create' % self._magento_model,
                          [customer_id, data])


@magento
class AddressImport(MagentoImportSynchronizer):
    _model_name = ['magento.address']

    def run(self, magento_id, address_infos):
        """ Run the synchronization """
        self.address_infos = address_infos
        return super(AddressImport, self).run(magento_id)

    def _get_magento_data(self):
        """ Return the raw Magento data for ``self.magento_id`` """
        # we already read the data from the Partner Importer
        if self.address_infos.magento_record:
            return self.address_infos.magento_record
        else:
            return super(AddressImport, self)._get_magento_data()

    def _define_partner_relationship(self, data):
        """ Link address with partner or parent company. """
        partner_binding_id = self.address_infos.partner_binding_id
        binder = self.binder_for('magento.res.partner')
        partner = binder.unwrap_binding(partner_binding_id, browse=True)
        if self.address_infos.merge:
            # it won't be imported as an independent address,
            # but will be linked with the main res.partner
            data['openerp_id'] = partner.id
            data['type'] = 'default'
        else:
            data['parent_id'] = partner.id
            data['lang'] = partner.lang
        data['magento_partner_id'] = self.address_infos.partner_binding_id
        return data

    def _create(self, data):
        data = self._define_partner_relationship(data)
        return super(AddressImport, self)._create(data)


@magento
class AddressImportMapper(BaseAddressImportMapper):
    _model_name = 'magento.address'

# TODO fields not mapped:
#   "suffix"=>"a",
#   "vat_id"=>"12334",

    direct = BaseAddressImportMapper.direct + [
        ('created_at', 'created_at'),
        ('updated_at', 'updated_at'),
        ('is_default_billing', 'is_default_billing'),
        ('is_default_shipping', 'is_default_shipping'),
        ('company', 'company'),
    ]

    @mapping
    def names(self, record):
        # TODO create a glue module for base_surname
        parts = [part for part in (record['firstname'],
                                   record.get('middlename'),
                                   record['lastname']) if part]
        return {'name': ' '.join(parts)}

    @mapping
    def use_parent_address(self, record):
        return {'use_parent_address': False}

    @mapping
    def type(self, record):
        if record.get('is_default_billing'):
            address_type = 'invoice'
        elif record.get('is_default_shipping'):
            address_type = 'delivery'
        else:
            address_type = 'contact'
        return {'type': address_type}


@job
def partner_import_batch(session, model_name, backend_id, filters=None):
    """ Prepare the import of partners modified on Magento """
    if filters is None:
        filters = {}
    assert 'magento_website_id' in filters, (
        'Missing information about Magento Website')
    env = get_environment(session, model_name, backend_id)
    importer = env.get_connector_unit(PartnerBatchImport)
    importer.run(filters=filters)
