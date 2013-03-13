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
class SaleOrderImportMapper(ImportMapper):
    _model_name = 'magento.sale.order'

    direct = [('increment_id', 'name'),
              ('increment_id', 'magento_id'),
              ('grand_total', 'total_amount'),
              ('tax_amount', 'total_amount_tax'),
              ('created_at', 'date_order'),
            ]

    @mapping
    def customer_id(self, record):
        binder = self.get_binder_for_model('magento.res.partner')
        partner_id = binder.to_openerp(record['customer_id'])
        assert partner_id is not None, \
               ("customer_id %s should have been imported in "
                "SaleOrderImport._import_dependencies" % record['customer_id'])
        return {'partner_id': partner_id}

    @mapping
    def payment(self, record):
        method_ids = self.session.search('payment.method',
                                         [['name', '=', record['payment']['method']]])
        if method_ids:
            method_id = method_ids[0]
        else:
            method_id = self.session.create('payment.method',
                                            {'name': record['payment']['method']})
        result = {'payment_method_id': method_id}
        return result

    @mapping
    def cod_fee(self, record): # cash on delivery
        # TODO Map Me (sic)
        pass

    @mapping
    def gift_cert_amount(self, record):
        result={'gift_certificates_amount': record['gift_cert_amount']}
        return result


    @mapping
    def gift_cert_code(self, record):
        result = {'gift_certificates_code': record['gift_cert_code']}
        return result

    @mapping
    def shipping_method(self, record):
        session = self.session
        ifield = record.get('shipping_method')
        if ifield:
            carrier_ids = session.search('delivery.carrier',
                                         [('magento_code', '=', ifield)])
        if carrier_ids:
            result = {'carrier_id': carrier_ids[0]}
        else:
            fake_partner_id = session.search('res.partner', [])[0]
            model_data_obj = session.pool['ir.model.data']
            model, product_id = model_data_obj.get_object_reference(session.cr, session.uid,
                                                                    'connector_ecommerce',
                                                                    'product_product_shipping')
            carrier_id = session.create('delivery.carrier',
                                        {'partner_id': fake_partner_id,
                                         'product_id': product_id,
                                         'name': ifield,
                                         'magento_code': ifield,
                                         })
            result = {'carrier_id': carrier_id}
        return result

    @mapping
    def base_shipping_incl_tax(self, record):
        amount_tax_inc = float(record.get('base_shipping_incl_tax', 0.0))
        discount = float(record.get('shipping_discount_amount', 0.0))
        amount_tax_inc -=  discount
        amount_tax_exc = float(record.get('shipping_amount', 0.0))

        if amount_tax_exc and amount_tax_inc:
            tax_rate = amount_tax_inc / amount_tax_exc -1
        else:
            tax_rate = 0

        result = {'shipping_amount_tax_included': amount_tax_inc,
                  'shipping_amount_tax_excluded': amount_tax_exc,
                  'shipping_tax_rate': tax_rate,
                  }
        return result

    # TODO:
    # billing address
    # shipping address
    # items (sale order lines)

    @mapping
    def items(self, record):
        for item in record['items']:
            pass


@magento
class SaleOrderLineImportMapper(ImportMapper):
    _model_name = 'magento.sale.order.line'

    direct = [('qty_ordered', 'product_uom_qty'),
              ('qty_ordered', 'product_uos_qty'),
              ('name', 'name'),
              ('product_id', 'product_id'),
              ('created_at', 'date_order'),
              ('customer_id', 'partner_id'),
              ('line_ext_id', 'magento_id'),
            ]

    @mapping
    def item_id(self, record):
        binder = self.get_binder_for_model('magento.product_product')
        product_id = binder.to_openerp(record['item_id'])
        assert product_id is not None, \
               ("item_id %s should have been imported in "
                "SaleOrderLineImport._import_dependencies" % record['item_id'])
        return {'product_id': product_id}

    @mapping
    def discount_amount(self, record):
        ifield = record.get('discount_amount')
        discount = 0
        if ifield:
            price = float(record['price'])
            qty_ordered = float(record['qty_ordered'])
            if price and qty_ordered:
                discount = float(100*ifield) / price * qty_ordered
        result = {'discount': discount}
        return result

    @mapping
    def product_options(self, record):
        result = {}
        ifield = record['product_options']
        if ifield:
            import re
            options_label = []
            clean = re.sub('\w:\w:|\w:\w+;', '', ifield)
            for each in clean.split('{'):
                if each.startswith('"label"'):
                    split_info = each.split(';')
                    options_label.append('%s: %s [%s]' % (split_info[1],
                                                          split_info[3],
                                                          record['sku']))
            result = {'notes':  "".join(options_label).replace('""', '\n').replace('"', '')}
        return result

    @mapping
    def price(self, record):
        base_row_total = float(record['base_row_total'])
        base_row_total_incl_tax = float(record['base_row_total_incl_tax'])
        qty_ordered = float(record['qty_ordered'])
        result = {'price_unit_tax_included': base_row_total_incl_tax / qty_ordered,
                  'price_unit_tax_excluded': base_row_total / qty_ordered,
                  'tax_rate': base_row_total and base_row_total_incl_tax / base_row_total - 1,
                  }
        return result
