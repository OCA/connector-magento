# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2011-2012 Camptocamp SA
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

{
    "name" : "Magento sku is product's code",
    "version" : "1.0",
    "depends" : ["base",
                 "product",
                 "magentoerpconnect",],
    "author" : "Camptocamp",
    "license": 'AGPL-3',
    "description": """Use product's code as SKU for Magento.
    Once exported to Magento, the Magento SKU is not changed, even if you change the product's code.
""",
    "website" : "http://www.camptocamp.com",
    "category" : "Generic Modules",
    "init_xml" : [],
    "demo_xml" : [],
    "update_xml" : ['product_view.xml'],
    "active": False,
    "installable": True,

}
