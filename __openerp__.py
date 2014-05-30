# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Chafique DELLI
#    Copyright 2014 Akretion
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

{'name': 'Magentoerpconnect Bundle Split',
 'version': '1.0.0',
 'category': 'Connector',
 'depends': [
    'magentoerpconnect',
    'sale_stock_relation_line',
    'sale_invoice_relation_line',
    ],
 'author': 'MagentoERPconnect Core Editors',
 'license': 'AGPL-3',
 'description': """
Magento Connector - BUNDLE SPLIT
=======================================
Extension for **Magento Connector**, add management of bundle products

Simple management of bundle items imported from Magento.

Each item choosed in a bundle is imported as a sale order line, so you are able to have correct margin and products turnover.

The bundle product is imported with a price of 0.0 or with the total price and is a service.

For the shipment, the first item which was part of the bundle create the full shipment on Magento (limitation because Magento wait for the bundle product).
The side effect is that the order will be marked as fully shipped on Magento even if the packing is sent in 2 times in OpenERP.
 """,
 'data': [],
 'installable': True,
 'application': False,
}
