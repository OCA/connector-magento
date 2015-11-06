# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2013-2015 Camptocamp SA
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

from openerp.addons.magentoerpconnect.backend import magento
from openerp.addons.magentoerpconnect import sale
from openerp.addons.connector.unit.mapper import mapping


@magento(replacing=sale.PricelistSaleOrderImportMapper)
class PricelistSaleOrderImportMapper(sale.PricelistSaleOrderImportMapper):
    _model_name = 'magento.sale.order'

    @mapping
    def pricelist_id(self, record):
        """ Assign to the sale order the price list used on
        the Magento Website or Backend """
        website_binder = self.binder_for('magento.website')
        website = website_binder.to_openerp(record['website_id'], browse=True)
        if website.pricelist_id:
            pricelist_id = website.pricelist_id.id
        else:
            pricelist_id = self.backend_record.pricelist_id.id
        return {'pricelist_id': pricelist_id}
