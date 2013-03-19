#########################################################################
#                                                                       #
# Copyright (C) 2009  Sharoon Thomas                                    #
# Copyright (C) 2011 Akretion Sébastien BEAU sebastien.beau@akretion.com#
# Copyright 2011-2013 Camptocamp SA                                     #
#                                                                       #
#This program is free software: you can redistribute it and/or modify   #
#it under the terms of the GNU General Public License as published by   #
#the Free Software Foundation, either version 3 of the License, or      #
#(at your option) any later version.                                    #
#                                                                       #
#This program is distributed in the hope that it will be useful,        #
#but WITHOUT ANY WARRANTY; without even the implied warranty of         #
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the          #
#GNU General Public License for more details.                           #
#                                                                       #
#You should have received a copy of the GNU General Public License      #
#along with this program.  If not, see <http://www.gnu.org/licenses/>.  #
#########################################################################
{
    "name": "Magento Connector New Generation",
    "version": "2.0.0",
    "depends": [
                 'account',
                 "product",
                 'delivery',
                 'sale_stock',
                 "connector_ecommerce",
                 "product_m2mcategories",
                 "product_images",
                 "product_links",
            ],
    "author": "MagentoERPconnect Core Editors",
    "license": "AGPL-3",  # TODO change the headers
    "description": """
Magento Connector
=================

TODO

""",
    'images': [  # TODO new images
        'images/main_menu.png',
        'images/instance.png',
        'images/sale_shop.png',
        'images/product.png',
        'images/magentocoreeditors.png',
        'images/magentoerpconnect.png',
    ],
    "website": "https://launchpad.net/magentoerpconnect",
    "category": "Connector",
    "demo": [],
    "data": [
            'security/ir.model.access.csv',
            'setting_view.xml',
            'magentoerpconnect_data.xml',
            'magento_model_view.xml',
            'product_view.xml',
            'partner_view.xml',
            'sale_view.xml',
            'product_images_view.xml',
            'magentoerpconnect_menu.xml',
            'delivery_view.xml',
            'product_links_view.xml',
            'stock_view.xml',
            ],
    "installable": True,
    'application': True,
}
