# -*- encoding: utf-8 -*-
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

from base_external_referentials.connector import (REGISTRY,
                                                  AbstractConnector,
                                                  AbstractMapping,
                                                  ModelMap)

class MagentoConnector(AbstractConnector):
    pass

class MagentoMapping(AbstractConnector):
    pass

class SaleOrderLineMap(ModelMap):
    model_name = 'sale.order.line'

class ResPartnerAddressMap(ModelMap):
    model_name = 'res.partner.address'

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
