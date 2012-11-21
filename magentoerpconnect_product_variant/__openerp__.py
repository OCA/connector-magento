# -*- encoding: utf-8 -*-
#################################################################################
#                                                                               #
#    Magentoerpconnect Product Variant for OpenERP                              #
#    Copyright (C) 2011 Akretion Sébastien BEAU <sebastien.beau@akretion.com>   #
#                                                                               #
#    This program is free software: you can redistribute it and/or modify       #
#    it under the terms of the GNU Affero General Public License as             #
#    published by the Free Software Foundation, either version 3 of the         #
#    License, or (at your option) any later version.                            #
#                                                                               #
#    This program is distributed in the hope that it will be useful,            #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of             #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the              #
#    GNU Affero General Public License for more details.                        #
#                                                                               #
#    You should have received a copy of the GNU Affero General Public License   #
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.      #
#                                                                               #
#################################################################################


{
    'name': 'magentoerpconnect_configurable_product',
    'version': '6.1.0',
    'category': 'Generic Modules',
    'license': 'AGPL-3',
    'description': """Module to extend the module magentoerpconnect, with it you will be able to create variant of product in magento directly from Openerp. Enjoy it !
NB: in magento the variant are called 'configurable product'""",
    'author': 'Akretion',
    'images': [
        'images/product_template.png',
        'images/dimension_type.png',
        'images/dimension_option.png',
        'images/magentocoreeditors.png',
        'images/magentoerpconnect.png',
    ],
    "website" : "https://launchpad.net/magentoerpconnect",
    'depends': ['magentoerpconnect', 'product_variant_multi'],
    'init_xml': [],
    'update_xml': [
            'product_view.xml',
#            'settings/1.3.2.4/external.mappinglines.template.csv',
            'settings/1.5.0.0/external.mappinglines.template.csv',
    ],
    'demo_xml': [],
    'installable': True,
    'active': False,
}

