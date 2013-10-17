# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2013 Camptocamp SA
#    Copyright 2013 Akretion
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


{'name': 'Magento Connector - Catalog',
 'version': '2.0.0',
 'category': 'Connector',
 'depends': ['magentoerpconnect',
             'product_custom_attributes',
             #'product_links',
             'product_image',
             ],
 'author': 'MagentoERPconnect Core Editors',
 'license': 'AGPL-3',
 'website': 'https://launchpad.net/magentoerpconnect',
 'description': """
Magento Connector - Catalog
===========================

Extension for **Magento Connector**, add management of the product's catalog:

Export
* products
* categories
* attributes (only export up to now): attribute set, attributes and attribute options :

   - to be used, you need to manually create an attribute set which match with magento 'Default' attribute set (generally magento_id '4')
   
* product image: dependency

   - dev branch: lp:~akretion-team/openerp-product-attributes/openerp-product-attributes-image
   - future production branch: lp:openerp-product-attributes/openerp-product-attributes

TODO:
* import/export product links
* import attributes
""",
 'images': [],
 'demo': [],
 'data': [
    'product_view.xml',
    'product_attribute_view.xml',
    'product_image_view.xml',
    ],
 'installable': True,
 'application': False,
}