# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Markus Schneider
#    Copyright 2014 initOS GmbH & Co. KG
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

from openerp.addons.connector.unit.mapper import mapping
from openerp.addons.magentoerpconnect.backend import magento
from openerp.addons.magentoerpconnect import product


@magento(replacing=product.IsActiveProductImportMapper)
class ProductImportMapper(product.IsActiveProductImportMapper):
    _model_name = 'magento.product.product'

    @mapping
    def is_active(self, record):
        """Check if the product is active in Magento
           and change acording the options"""
        is_active = (record.get('status') == '1')

        if self.backend_record.product_active == 'nothing':
            return {}
        if self.backend_record.product_active == 'disable':
            return {'active': is_active}
        if self.backend_record.product_active == 'no_sale':
            return {'sale_ok': is_active}
        if self.backend_record.product_active == 'no_sale_no_purchase':
            return {'sale_ok': is_active,
                    'purchase_ok': is_active}
