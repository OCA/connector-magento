# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.connector.unit.mapper import mapping, changed_by
from odoo.addons.connector.exception import InvalidDataError
from odoo.addons.component.core import Component


class PartnerExporter(Component):
    _name = 'magento.partner.exporter'
    _inherit = 'magento.exporter'
    _apply_on = ['magento.res.partner']

    def _after_export(self):
        # Condition on street field because we consider that if street
        # is false, there is no address to export on this partner.
        if (not self.binding.magento_address_bind_ids and
                not self.binding.consider_as_company and
                self.binding.street):
            extra_vals = {
                'is_default_billing': True,
                'magento_partner_id': self.binding.id,
            }
            if not self.binding.child_ids:
                extra_vals['is_default_shipping'] = True
            self._export_dependency(self.binding.odoo_id,
                                    'magento.address',
                                    binding_field='magento_address_bind_ids',
                                    binding_extra_vals=extra_vals)

        for child in self.binding.child_ids:
            child_extra_vals = {
                'magento_partner_id': self.binding.id,
            }
            if not child.magento_address_bind_ids:
                if child.type == 'invoice':
                    child_extra_vals['is_default_billing'] = True
                if child.type == 'delivery':
                    child_extra_vals['is_default_shipping'] = True
                self._export_dependency(
                    child, 'magento.address',
                    binding_field='magento_address_bind_ids',
                    binding_extra_vals=child_extra_vals)

    def _validate_create_data(self, data):
        """ Check if the values to import are correct

        Pro-actively check before the ``Model.create`` or
        ``Model.update`` if some fields are missing

        Raise `InvalidDataError`
        """
        if not data.get('email'):
            raise InvalidDataError("The partner does not have an email "
                                   "but it is mandatory for Magento")
        return


class AddressExporter(Component):
    _name = 'magento.address.exporter'
    _inherit = 'magento.exporter'
    _apply_on = ['magento.address']

    def _export_dependencies(self):
        """ Export the dependencies for the record"""
        relation = (self.binding.parent_id or
                    self.binding.odoo_id)
        self._export_dependency(relation, 'magento.res.partner')

    def _validate_create_data(self, data):
        """ Check if the values to import are correct

        Pro-actively check before the ``Model.create`` or
        ``Model.update`` if some fields are missing

        Raise `InvalidDataError`
        """
        missing_fields = []
        for required_key in ('city', 'street', 'postcode',
                             'country_id', 'telephone'):
            if not data.get(required_key):
                missing_fields.append(required_key)
        if missing_fields:
            raise InvalidDataError("The address does not contain one or "
                                   "several mandatory fields for "
                                   "Magento: %s" %
                                   missing_fields)

    def _create(self, data):
        """ Create the Magento record """
        # special check on data before export
        self._validate_create_data(data)
        customer_id = data.pop('customer_id')
        return self.backend_adapter.create(customer_id, data)


class PartnerExportMapper(Component):
    _name = 'magento.partner.export.mapper'
    _inherit = 'magento.export.mapper'
    _apply_on = ['magento.res.partner']

    direct = [
        ('birthday', 'dob'),
        ('taxvat', 'taxvat'),
        ('group_id', 'group_id'),
        ('website_id', 'website_id'),
    ]

    @changed_by('email', 'emailid')
    @mapping
    def email(self, record):
        email = record.emailid or record.email
        return {'email': email}

    @changed_by('name', 'firstname', 'lastname')
    @mapping
    def names(self, record):
        if 'firstname' in record._fields:
            firstname = record.firstname
            lastname = record.lastname
        else:
            if ' ' in record.name:
                parts = record.name.split()
                firstname = parts[0]
                lastname = ' '.join(parts[1:])
            else:
                lastname = record.name
                firstname = '-'
        return {'firstname': firstname, 'lastname': lastname}


class PartnerAddressExportMapper(Component):
    _name = 'magento.address.export.mapper'
    _inherit = 'magento.export.mapper'
    _apply_on = ['magento.address']

    direct = [('zip', 'postcode'),
              ('city', 'city'),
              ('is_default_billing', 'is_default_billing'),
              ('is_default_shipping', 'is_default_shipping'),
              ('company', 'company'),
              ]

    @changed_by('parent_id', 'openerp_id')
    @mapping
    def partner(self, record):
        binder = self.binder_for('magento.res.partner')
        if record.parent_id:
            erp_partner = record.parent_id
        else:
            erp_partner = record.odoo_id
        mag_partner_id = binder.to_external(erp_partner, wrap=True)
        return {'customer_id': mag_partner_id}

    @changed_by('name', 'firstname', 'lastname')
    @mapping
    def names(self, record):
        if 'firstname' in record._fields:
            firstname = record.firstname or record.parent_id.firstname
            lastname = record.lastname or record.parent_id.lastname
        else:
            name = record.name or record.parent_id.name
            if ' ' in name:
                parts = name.split()
                firstname = parts[0]
                lastname = ' '.join(parts[1:])
            else:
                lastname = name
                firstname = '-'
        return {'firstname': firstname, 'lastname': lastname}

    @changed_by('phone', 'mobile')
    @mapping
    def phone(self, record):
        return {'telephone': record.phone or record.mobile}

    @changed_by('country_id')
    @mapping
    def country(self, record):
        if record.country_id:
            return {'country_id': record.country_id.code}

    @changed_by('state_id')
    @mapping
    def region(self, record):
        if record.state_id:
            return {'region': record.state_id.name}

    @changed_by('street', 'street2')
    @mapping
    def street(self, record):
        street = False
        if record.street:
            street = record.street
        if record.street2:
            street = ['\n'.join([street, record.street2])]
        if street:
            return {'street': street}
