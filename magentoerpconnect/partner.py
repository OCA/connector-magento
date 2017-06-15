# -*- coding: utf-8 -*-
# © 2013 Guewen Baconnier,Camptocamp SA,Akretion
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import xmlrpclib
from collections import namedtuple
from odoo import models, fields, api
from odoo.addons.queue_job.job import job
from odoo.addons.component.core import AbstractComponent, Component

from odoo.addons.connector.exception import MappingError, IDMissingInBackend
from odoo.addons.connector.components.mapper import mapping, only_create
from .components.backend_adapter import MAGENTO_DATETIME_FORMAT
from .components.mapper import normalize_datetime

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    magento_bind_ids = fields.One2many(
        comodel_name='magento.res.partner',
        inverse_name='odoo_id',
        string="Magento Bindings",
    )
    magento_address_bind_ids = fields.One2many(
        comodel_name='magento.address',
        inverse_name='odoo_id',
        string="Magento Address Bindings",
    )
    birthday = fields.Date(string='Birthday')
    company = fields.Char(string='Company')

    @api.model
    def _address_fields(self):
        """ Returns the list of address fields that are synced from the
        parent.

        """
        fields = super(ResPartner, self)._address_fields()
        fields.append('company')
        return fields

    @job(default_channel='root.magento')
    @api.model
    def import_batch(self, backend, filters=None):
        assert 'magento_website_id' in filters, (
            'Missing information about Magento Website')
        return super(ResPartner, self).import_batch(backend, filters=filters)


class MagentoResPartner(models.Model):
    _name = 'magento.res.partner'
    _inherit = 'magento.binding'
    _inherits = {'res.partner': 'odoo_id'}
    _description = 'Magento Partner'

    _rec_name = 'name'

    odoo_id = fields.Many2one(comodel_name='res.partner',
                              string='Partner',
                              required=True,
                              ondelete='cascade')
    backend_id = fields.Many2one(
        related='website_id.backend_id',
        comodel_name='magento.backend',
        string='Magento Backend',
        store=True,
        readonly=True,
        # override 'magento.binding', can't be INSERTed if True:
        required=False,
    )
    website_id = fields.Many2one(comodel_name='magento.website',
                                 string='Magento Website',
                                 required=True,
                                 ondelete='restrict')
    group_id = fields.Many2one(comodel_name='magento.res.partner.category',
                               string='Magento Group (Category)')
    created_at = fields.Datetime(string='Created At (on Magento)',
                                 readonly=True)
    updated_at = fields.Datetime(string='Updated At (on Magento)',
                                 readonly=True)
    emailid = fields.Char(string='E-mail address')
    taxvat = fields.Char(string='Magento VAT')
    newsletter = fields.Boolean(string='Newsletter')
    guest_customer = fields.Boolean(string='Guest Customer')
    consider_as_company = fields.Boolean(
        string='Considered as company',
        help="An account imported with a 'company' in "
             "the billing address is considered as a company.\n "
             "The partner takes the name of the company and "
             "is not merged with the billing address.",
    )


class MagentoAddress(models.Model):
    _name = 'magento.address'
    _inherit = 'magento.binding'
    _inherits = {'res.partner': 'odoo_id'}
    _description = 'Magento Address'

    _rec_name = 'backend_id'

    odoo_id = fields.Many2one(comodel_name='res.partner',
                              string='Partner',
                              required=True,
                              ondelete='cascade')
    created_at = fields.Datetime(string='Created At (on Magento)',
                                 readonly=True)
    updated_at = fields.Datetime(string='Updated At (on Magento)',
                                 readonly=True)
    is_default_billing = fields.Boolean(string='Default Invoice')
    is_default_shipping = fields.Boolean(string='Default Shipping')
    magento_partner_id = fields.Many2one(comodel_name='magento.res.partner',
                                         string='Magento Partner',
                                         required=True,
                                         ondelete='cascade')
    backend_id = fields.Many2one(
        related='magento_partner_id.backend_id',
        comodel_name='magento.backend',
        string='Magento Backend',
        store=True,
        readonly=True,
        # override 'magento.binding', can't be INSERTed if True:
        required=False,
    )
    website_id = fields.Many2one(
        related='magento_partner_id.website_id',
        comodel_name='magento.website',
        string='Magento Website',
        store=True,
        readonly=True,
    )
    is_magento_order_address = fields.Boolean(
        string='Address from a Magento Order',
    )

    _sql_constraints = [
        ('odoo_uniq', 'unique(backend_id, odoo_id)',
         'A partner address can only have one binding by backend.'),
    ]


class PartnerAdapter(Component):

    _name = 'magento.partner.adapter'
    _inherit = 'magento.adapter'
    _apply_on = 'magento.res.partner'

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


class PartnerBatchImporter(Component):
    """ Import the Magento Partners.

    For every partner in the list, a delayed job is created.
    """
    _name = 'magento.partner.batch.importer'
    _inherit = 'magento.delayed.batch.importer'
    _apply_on = 'magento.res.partner'

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


class PartnerImportMapper(Component):
    _name = 'magento.partner.import.mapper'
    _inherit = 'magento.import.mapper'
    _apply_on = 'magento.res.partner'

    direct = [
        ('email', 'email'),
        ('dob', 'birthday'),
        (normalize_datetime('created_at'), 'created_at'),
        (normalize_datetime('updated_at'), 'updated_at'),
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
        parts = [part for part in (record['firstname'],
                                   record['middlename'],
                                   record['lastname']) if part]
        return {'name': ' '.join(parts)}

    @mapping
    def customer_group_id(self, record):
        # import customer groups
        binder = self.binder_for(model='magento.res.partner.category')
        category = binder.to_internal(record['group_id'], unwrap=True)

        if not category:
            raise MappingError("The partner category with "
                               "magento id %s does not exist" %
                               record['group_id'])

        # FIXME: should remove the previous tag (all the other tags from
        # the same backend)
        return {'category_id': [(4, category.id)]}

    @mapping
    def website_id(self, record):
        binder = self.binder_for(model='magento.website')
        website = binder.to_internal(record['website_id'])
        return {'website_id': website.id}

    @only_create
    @mapping
    def company_id(self, record):
        binder = self.binder_for(model='magento.storeview')
        storeview = binder.to_internal(record['store_id'])
        if storeview:
            company = storeview.backend_id.company_id
            if company:
                return {'company_id': company.id}
        return {'company_id': False}

    @mapping
    def lang(self, record):
        binder = self.binder_for(model='magento.storeview')
        storeview = binder.to_internal(record['store_id'])
        if storeview:
            if storeview.lang_id:
                return {'lang': storeview.lang_id.code}

    @only_create
    @mapping
    def customer(self, record):
        return {'customer': True}

    @mapping
    def type(self, record):
        return {'type': 'contact'}

    @only_create
    @mapping
    def odoo_id(self, record):
        """ Will bind the customer on a existing partner
        with the same email """
        partner = self.env['res.partner'].search(
            [('email', '=', record['email']),
             ('customer', '=', True),
             '|',
             ('is_company', '=', True),
             ('parent_id', '=', False)],
            limit=1,
        )
        if partner:
            return {'odoo_id': partner.id}


class PartnerImporter(Component):
    _name = 'magento.partner.importer'
    _inherit = 'magento.importer'
    _apply_on = 'magento.res.partner'

    def _import_dependencies(self):
        """ Import the dependencies for the record"""
        record = self.magento_record
        self._import_dependency(record['group_id'],
                                'magento.res.partner.category')

    def _after_import(self, partner_binding):
        """ Import the addresses """
        book = self.component(usage='address.book',
                              model_name='magento.address')
        book.import_addresses(self.external_id, partner_binding.id)


AddressInfos = namedtuple('AddressInfos', ['magento_record',
                                           'partner_binding_id',
                                           'merge'])


class PartnerAddressBook(Component):
    """ Import all addresses from the address book of a customer.

        This class is responsible to define which addresses should
        be imported and how (merge with the partner or not...).
        Then, it delegate the import to the appropriate importer.

        This is really intricate. The datamodel are different between
        Magento and Odoo and we have many uses cases to cover.

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
    _name = 'magento.address.book'
    _inherit = 'base.magento.connector'
    _apply_on = 'magento.address'
    _usage = 'address.book'

    def import_addresses(self, magento_partner_id, partner_binding_id):
        addresses = self._get_address_infos(magento_partner_id,
                                            partner_binding_id)
        for address_id, infos in addresses:
            importer = self.component(usage='record.importer')
            importer.run(address_id, address_infos=infos)

    def _get_address_infos(self, magento_partner_id, partner_binding_id):
        adapter = self.component(usage='backend.adapter')
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
                binding_model = self.env['magento.res.partner']
                partner_binding = binding_model.browse(partner_binding_id)
                if magento_record.get('company'):
                    # when a company is there, we never merge the contact
                    # with the partner.
                    # Copy the billing address on the company
                    # and use the name of the company for the name
                    company_mapper = self.component(
                        usage='company.import.mapper',
                        model_name='magento.res.partner'
                    )
                    map_record = company_mapper.map_record(magento_record)
                    parent = partner_binding.odoo_id.parent_id
                    values = map_record.values(parent_partner=parent)
                    partner_binding.write(values)
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


class BaseAddressImportMapper(AbstractComponent):
    """ Defines the base mappings for the imports
    in ``res.partner`` (state, country, ...)
    """

    _name = 'magento.base.address.import.mapper'
    _inherit = 'magento.import.mapper'

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
        state = self.env['res.country.state'].search(
            [('name', '=ilike', record['region'])],
            limit=1,
        )
        if state:
            return {'state_id': state.id}

    @mapping
    def country(self, record):
        if not record.get('country_id'):
            return
        country = self.env['res.country'].search(
            [('code', '=', record['country_id'])],
            limit=1,
        )
        if country:
            return {'country_id': country.id}

    @mapping
    def street(self, record):
        value = record['street']
        if not value:
            return {}
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
        title = self.env['res.partner.title'].search(
            [('shortcut', '=ilike', prefix)],
            limit=1
        )
        if not title:
            title = self.env['res.partner.title'].create(
                {'shortcut': prefix,
                 'name': prefix,
                 }
            )
        return {'title': title.id}

    @only_create
    @mapping
    def company_id(self, record):
        parent = self.options.parent_partner
        if parent:
            if parent.company_id:
                return {'company_id': parent.company_id.id}
            else:
                return {'company_id': False}
        # Don't return anything, we are merging into an existing partner
        return


class CompanyImportMapper(Component):
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

    _name = 'magento.company.import.mapper'
    _inherit = 'magento.base.address.import.mapper'
    _apply_on = 'magento.res.partner'
    _usage = 'company.import.mapper'

    @property
    def direct(self):
        fields = super(CompanyImportMapper, self).direct[:]
        return fields + [('company', 'name')]

    @mapping
    def consider_as_company(self, record):
        return {'consider_as_company': True}


class AddressAdapter(Component):

    _name = 'magento.address.adapter'
    _inherit = 'magento.adapter'
    _apply_on = 'magento.address'

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


class AddressImporter(Component):

    _name = 'magento.address.importer'
    _inherit = 'magento.importer'
    _apply_on = 'magento.address'

    def run(self, external_id, address_infos=None, force=False):
        """ Run the synchronization """
        if address_infos is None:
            # only possible for updates
            self.address_infos = AddressInfos(None, None, None)
        else:
            self.address_infos = address_infos
        return super(AddressImporter, self).run(external_id, force=force)

    def _get_magento_data(self):
        """ Return the raw Magento data for ``self.external_id`` """
        # we already read the data from the Partner Importer
        if self.address_infos.magento_record:
            return self.address_infos.magento_record
        else:
            return super(AddressImporter, self)._get_magento_data()

    def _define_partner_relationship(self, data):
        """ Link address with partner or parent company. """
        partner_binding_id = self.address_infos.partner_binding_id
        assert partner_binding_id, ("AdressInfos are required for creation of "
                                    "a new address.")
        binder = self.binder_for('magento.res.partner')
        partner = binder.unwrap_binding(partner_binding_id)
        if self.address_infos.merge:
            # it won't be imported as an independent address,
            # but will be linked with the main res.partner
            data['odoo_id'] = partner.id
            data['type'] = 'contact'
        else:
            data['parent_id'] = partner.id
            data['lang'] = partner.lang
        data['magento_partner_id'] = self.address_infos.partner_binding_id
        return data

    def _create(self, data):
        data = self._define_partner_relationship(data)
        return super(AddressImporter, self)._create(data)


class AddressImportMapper(Component):

    _name = 'magento.address.import.mapper'
    _inherit = 'magento.base.address.import.mapper'
    _apply_on = 'magento.address'

    @property
    def direct(self):
        fields = super(AddressImportMapper, self).direct[:]
        fields += [
            ('created_at', 'created_at'),
            ('updated_at', 'updated_at'),
            ('is_default_billing', 'is_default_billing'),
            ('is_default_shipping', 'is_default_shipping'),
            ('company', 'company'),
        ]
        return fields

    @mapping
    def names(self, record):
        parts = [part for part in (record['firstname'],
                                   record.get('middlename'),
                                   record['lastname']) if part]
        return {'name': ' '.join(parts)}

    @mapping
    def type(self, record):
        if record.get('is_default_billing'):
            address_type = 'invoice'
        elif record.get('is_default_shipping'):
            address_type = 'delivery'
        else:
            address_type = 'other'
        return {'type': address_type}
