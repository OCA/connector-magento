# -*- coding: utf-8 -*-
###############################################################################
#                                                                             #
#   product_custom_attributes for OpenERP                                     #
#   Copyright (C) 2012 Camptocamp Alexandre Fayolle  <alexandre.fayolle@camptocamp.com>  #
#   Copyright (C) 2012 Akretion Sebastien Beau <sebastien.beau@akretion.com>  #
#                                                                             #
#   This program is free software: you can redistribute it and/or modify      #
#   it under the terms of the GNU Affero General Public License as            #
#   published by the Free Software Foundation, either version 3 of the        #
#   License, or (at your option) any later version.                           #
#                                                                             #
#   This program is distributed in the hope that it will be useful,           #
#   but WITHOUT ANY WARRANTY; without even the implied warranty of            #
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the             #
#   GNU Affero General Public License for more details.                       #
#                                                                             #
#   You should have received a copy of the GNU Affero General Public License  #
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.     #
#                                                                             #
###############################################################################

from openerp.addons.connector.connector import (REGISTRY,
                                                AbstractMapping,
                                                ModelMap)
from openerp.addons.connector_ecommerce.connector import BaseConnector

class MagentoConnector(BaseConnector):
    '''need to recode
    def _import_<model_name>(self, cr, uid, res_obj, defaults, context):
        pass
    def _get_import_defaults_<model_name>(self, cr, uid, context):
        pass
    def _import_<model_name>(self, cr, uid, res_obj, defaults, context):
        pass
    def _get_import_step_<model_name>(self, res_obj, context):
        pass
    def _record_one_<model_name>(self, cr, uid, res_obj, resource, defaults, context):
        pass
    def _oe_update_<model_name>(self, cr, uid, res_obj, existing_rec_id, vals, resource, defaults, context):
        pass
    * _oe_create_<model_name>(self, cr, uid, res_obj, vals, resource, defaults, context):
        pass
    '''
    @classmethod
    def match(cls, type, version):
        raise NotImplementedError # do something smart here
    
    def _get_filter_sale_order(self, cr, uid, res_obj, step, previous_filter, context):
        pass
    def _get_filter_magerp_product_attribute_groups(self, cr, uid, res_obj, step, previous_filter,
                                                    context):
        pass

    def _ext_search_product_category(self, xxx):
        pass

    def _ext_search_sale_order(self, xxx):
        pass

    def _get_import_defaults_sale_shop(self, cr, uid, context=None):
        pass

    def _default_ext_search(self, xxx):
        pass

    def _default_ext_read(self, xxx):
        pass

    def _default_ext_read_product_product(self, xxx):
        pass

    def _record_one_sale_order(self, cr, uid, res_obj, resource, defaults, context):
        pass

REGISTRY.register_connector(MagentoConnector)


class MagentoMapping(AbstractConnector):
    pass

class MagentoMapping1500(MagentoMapping):
    pass

REGISTRY.register_mapping(MagentoMapping1500)

class SaleOrderLineMap(ModelMap):
    model_name = 'sale.order.line'
MagentoMapping1500.register_model_map(SaleOrderLineMap)


class SaleOrderMap(ModelMap):
    model_name = 'sale.order'
    _external_id_key = 'increment_id'
    direct_import = [('increment_id', 'name'),
                     ('grand_total', 'ext_total_amount'),
                     ('customer_id', 'partner_id'),
                     ('created_at', 'date_order'),
                     ('cod_fee', 'gift_certificate_amount'),
                     ('shipping_amount', 'shipping_amount_tax_excluded'),
                     ('base_shipping_incl_tax', 'shipping_amount_tax_included'),
                     ('giftcert_code', 'gift_certificates_code'),
                     ('giftcert_amount', 'gift_certificates_amount'),
                     ]

    def import_payment(self, cr, uid, ext_attr, ext_resource, oerp_value, context=None):
        pass
    def import_shipping_method(self, cr, uid, ext_attr, ext_resource, oerp_value, context=None):
        pass
    function_import = [('payment', import_payment),
                       ('shipping_method', import_shipping_method),
                       ]
    submapping_import = [('items', ('order_line', SaleOrderLineMap)),
                         ('shipping_address', ('partner_shipping_id', ResPartnerAddressMap)),
                         ('billing_address', ('partner_invoice_id', ResPartnerAddressMap)),
                         ]
MagentoMapping1500.register_model_map(SaleOrderMap)
