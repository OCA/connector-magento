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
                 "connector_ecommerce",
                 "product_m2mcategories",
                 "product_images",
                 "product_links",
            ],
    "author": "MagentoERPconnect Core Editors",
    "description": """
Magento Connector
=================

TODO

""",
    'images': [
        'images/main_menu.png',
        'images/instance.png',
        'images/sale_shop.png',
        'images/product.png',
        'images/magentocoreeditors.png',
        'images/magentoerpconnect.png',
    ],
    "website": "https://launchpad.net/magentoerpconnect",
    "category": "Connector",
    "init_xml": ['settings/magerp.product_category_attribute_options.csv',
                 'magentoerpconnect_data.xml'],
    "demo_xml": [],
    "update_xml": [
            'security/ir.model.access.csv',
            'setting_view.xml',
            'magerp_data.xml',
            'magento_model_view.xml',
            'product_view.xml',
            'partner_view.xml',
            'sale_view.xml',
            'product_images_view.xml',
            'magento_menu.xml',
            'delivery_view.xml',
            'product_links_view.xml',
            'wizard/open_product_by_attribut_set.xml',
            ],
    "installable": True,
    'application': True,
}
