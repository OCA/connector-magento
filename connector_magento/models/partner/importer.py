# Copyright 2013-2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging

from collections import namedtuple
from odoo.addons.component.core import AbstractComponent, Component
from odoo.addons.connector.exception import MappingError
from odoo.addons.connector.components.mapper import mapping, only_create
from ...components.mapper import normalize_datetime

_logger = logging.getLogger(__name__)


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
        """ Middlename not always present in Magento 2 """
        # TODO Check on first run
        parts = [part for part in (record['firstname'],
                                   record.get('middlename'),
                                   record['lastname']) if part]
        return {'name': ' '.join(parts)}

    @mapping
    def customer_group_id(self, record):
        # import customer groups
        if record['group_id'] == 0:
            category = self.env.ref('connector_magento.category_no_account')
        else:
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
        if self.backend_record.is_multi_company:
            return {'company_id': False}
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

    def _read_addresses(self, magento_partner_id):
        """ Provide addresses
        - Magento 1.x: read the addresses from the address repository
        - Magento 2.x: addresses are included in the partner record
        """
        if self.collection.version == '1.7':
            adapter = self.component(usage='backend.adapter')
            mag_address_ids = adapter.search({'customer_id':
                                              {'eq': magento_partner_id}})
            return [(address_id, adapter.read(address_id))
                    for address_id in mag_address_ids]

        with self.collection.work_on('magento.res.partner') as partner:
            adapter = partner.component(usage='backend.adapter')
            record = adapter.read(magento_partner_id)
        return [(addr['id'], addr) for addr in record['addresses']]

    def _get_address_infos(self, magento_partner_id, partner_binding_id):
        for address_id, magento_record in self._read_addresses(
                magento_partner_id):
            # defines if the billing address is merged with the partner
            # or imported as a standalone contact
            merge = False
            if (magento_record.get('is_default_billing')  # Magento 1.x
                    or magento_record.get('default_billing')):  # Magento 2.x
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
        """ 'street' can be presented as a list in Magento2 """
        value = record['street']
        if not value:
            return {}
        if isinstance(value, list):
            lines = value
        else:
            lines = [line.strip() for line in value.split('\n')
                     if line.strip()]
        if len(lines) == 1:
            result = {'street': lines[0], 'street2': False}
        elif len(lines) >= 2:
            result = {'street': lines[0], 'street2': ' - '.join(lines[1:])}
        else:
            result = {}
        return result

    @mapping
    def title(self, record):
        """ Prefix is optionally present in Magento 2 """
        prefix = record.get('prefix')
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
        if self.backend_record.is_multi_company:
            return {'company_id': False}
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
            ('company', 'company'),
        ]
        return fields

    @staticmethod
    def is_billing(record):
        return (
            record.get('default_billing')  # Magento 2.x
            or record.get('is_default_billing'))  # Magento 1.x

    @staticmethod
    def is_shipping(record):
        return (
            record.get('default_shipping')  # Magento 2.x
            or record.get('is_default_shipping'))  # Magento 1.x

    @mapping
    def default_billing(self, record):
        return {'is_default_billing': self.is_billing(record)}

    def default_shipping(self, record):
        return {'default_shipping': self.is_shipping(record)}

    @mapping
    def names(self, record):
        parts = [part for part in (record['firstname'],
                                   record.get('middlename'),
                                   record['lastname']) if part]
        return {'name': ' '.join(parts)}

    @mapping
    def type(self, record):
        if self.is_billing(record):
            address_type = 'invoice'
        elif self.is_shipping(record):
            address_type = 'delivery'
        else:
            address_type = 'other'
        return {'type': address_type}
