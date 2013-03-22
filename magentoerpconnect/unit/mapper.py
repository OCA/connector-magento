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

from openerp.tools.translate import _
from openerp.addons.connector.exception import MappingError
from openerp.addons.connector.unit.mapper import (mapping,
                                                  changed_by,
                                                  ImportMapper,
                                                  ExportMapper)
from openerp.addons.connector_ecommerce.unit.sale_order_onchange import SaleOrderOnChange
from ..backend import magento

_logger = logging.getLogger(__name__)


@magento
class WebsiteImportMapper(ImportMapper):
    _model_name = 'magento.website'

    direct = [('code', 'code'),
              ('sort_order', 'sort_order')]

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
        ('code', 'code'),
        ('is_active', 'enabled'),
        ('sort_order', 'sort_order'),
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


@magento
class ProductCategoryImportMapper(ImportMapper):
    _model_name = 'magento.product.category'

    direct = [
            ('description', 'description'),
            ]

    @mapping
    def name(self, record):
        if record['level'] == '0':  # top level category; has no name
            return {'name': self.backend_record.name}
        if record['name']:  # may be empty in storeviews
            return {'name': record['name']}

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
        category_id = binder.to_openerp(record['parent_id'], unwrap=True)
        mag_cat_id = binder.to_openerp(record['parent_id'])

        if category_id is None:
            raise MappingError("The product category with "
                               "magento id %s is not imported." %
                               record['parent_id'])
        return {'parent_id': category_id, 'magento_parent_id': mag_cat_id}


@magento
class SaleOrderImportMapper(ImportMapper):
    _model_name = 'magento.sale.order'

    direct = [('increment_id', 'name'),
              ('increment_id', 'magento_id'),
              ('order_id', 'magento_order_id'),
              ('grand_total', 'total_amount'),
              ('tax_amount', 'total_amount_tax'),
              ('created_at', 'date_order'),
              ]

    children = [('items', 'magento_order_line_ids', 'magento.sale.order.line'),
                ]

    def _after_mapping(self, result):
        sess = self.session
        result = sess.pool['sale.order']._convert_special_fields(sess.cr,
                                                                 sess.uid,
                                                                 result,
                                                                 result['magento_order_line_ids'],
                                                                 sess.context)
        onchange = self.get_connector_unit_for_model(SaleOrderOnChange)
        return onchange.play(result, result['magento_order_line_ids'])

    @mapping
    def store_id(self, record):
        binder = self.get_binder_for_model('magento.storeview')
        storeview_id = binder.to_openerp(record['store_id'])
        assert storeview_id is not None, 'cannot import sale orders from non existinge storeview'
        storeview = self.session.browse('magento.storeview', storeview_id)
        shop_id = storeview.store_id.openerp_id.id
        return {'shop_id': shop_id}

    @mapping
    def customer_id(self, record):
        binder = self.get_binder_for_model('magento.res.partner')
        partner_id = binder.to_openerp(record['customer_id'], unwrap=True)
        assert partner_id is not None, \
               ("customer_id %s should have been imported in "
                "SaleOrderImport._import_dependencies" % record['customer_id'])
        return {'partner_id': partner_id}

    @mapping
    def payment(self, record):
        method_ids = self.session.search('payment.method',
                                         [['name', '=', record['payment']['method']]])
        assert method_ids, ("method %s should exist because the import fails "
                            "in SaleOrderImport._before_import when it is "
                            " missing" % record['payment']['method'])
        method_id = method_ids[0]
        return {'payment_method_id': method_id}

    @mapping
    def cod_fee(self, record): # cash on delivery
        # TODO Map Me (sic)
        pass

    @mapping
    def gift_cert_amount(self, record):
        if 'gift_cert_amount' in record:
            result = {'gift_certificates_amount': record['gift_cert_amount']}
        else:
            result = {}
        return result

    @mapping
    def gift_cert_code(self, record):
        if 'gift_cert_code' in record:
            result = {'gift_certificates_code': record['gift_cert_code']}
        else:
            result = {}
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

    # partner_id, partner_invoice_id, partner_shipping_id
    # are done in the importer

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}

@magento
class MagentoSaleOrderOnChange(SaleOrderOnChange):
    _model_name = 'magento.sale.order'


@magento
class SaleOrderLineImportMapper(ImportMapper):
    _model_name = 'magento.sale.order.line'

    direct = [('qty_ordered', 'product_uom_qty'),
              ('qty_ordered', 'product_uos_qty'),
              ('name', 'name'),
              ('item_id', 'magento_id'),
            ]

    @mapping
    def product_id(self, record):
        binder = self.get_binder_for_model('magento.product.product')
        product_id = binder.to_openerp(record['product_id'], unwrap=True)
        assert product_id is not None, \
               ("product_id %s should have been imported in "
                "SaleOrderImport._import_dependencies" % record['product_id'])
        return {'product_id': product_id}

    @mapping
    def discount_amount(self, record):
        ifield = record.get('discount_amount')
        discount = 0
        if ifield:
            price = float(record['price'])
            qty_ordered = float(record['qty_ordered'])
            if price and qty_ordered:
                discount = 100 * float(ifield) / price * qty_ordered
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
        result = {}
        backend = self.backend_record
        base_row_total = float(record['base_row_total'] or 0.)
        base_row_total_incl_tax = float(record['base_row_total_incl_tax'] or 0.)
        qty_ordered = float(record['qty_ordered'])
        if backend.catalog_price_tax_included:
            result['price_unit'] = base_row_total_incl_tax / qty_ordered
        else:
            result['price_unit'] = base_row_total / qty_ordered
        return result


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
    def categories(self, record):
        mag_categories = record['categories']
        binder = self.get_binder_for_model('magento.product.category')

        category_ids = []
        main_categ_id = None

        for mag_category_id in mag_categories:
            cat_id = binder.to_openerp(mag_category_id, unwrap=True)
            if cat_id is None:
                raise MappingError("The product category with "
                                   "magento id %s is not imported." %
                                   mag_category_id)

            category_ids.append(cat_id)

        if category_ids:
            main_categ_id = category_ids.pop(0)

        if main_categ_id is None:
            default_categ = self.backend_record.default_category_id
            if default_categ:
                main_categ_id = default_categ.id

        result = {'categ_ids': [(6, 0, category_ids)]}
        if main_categ_id:  # OpenERP assign 'All Products' if not specified
            result['categ_id'] = main_categ_id
        return result

    @mapping
    def magento_id(self, record):
        return {'magento_id': record['product_id']}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}
