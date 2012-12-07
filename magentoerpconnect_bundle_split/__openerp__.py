# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2012 Camptocamp SA
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
    'name': 'Magentoerpconnect Bundle Split',
    'version': '6.1.0',
    'category': 'Generic Modules',
    "author" : "Camptocamp",
    'license': 'AGPL-3',
    'description': """Module to extend the module magentoerpconnect.
Simple management of bundle items imported from Magento.

Each item choosed in a bundle is imported as a sale order line, so you are able to have correct margin and products turnover.

The bundle product is imported with a price of 0.0 and is a service.

For the shipment, the first item which was part of the bundle create the full shipment on Magento (limitation because Magento wait for the bundle product).
The side effect is that the order will be marked as fully shipped on Magento even if the packing is sent in 2 times in OpenERP.

This module is not compatible with "magentoerpconnect_bundle" as it does not handle the bundles the same way.
magentoerpconnect_bundle: products configurator for bundles with production orders for sub-items
magentoerpconnect_bundle_split: sub-items are managed as normal products in OpenERP, no configurator
""",
    'images': ['images/magentocoreeditors.png',
               'images/magentoerpconnect.png',],
    "website" : "https://launchpad.net/magentoerpconnect",
    'depends': ['magentoerpconnect'],
    'init_xml': [],
    'update_xml': [
           'settings/1.5.0.0/external.mappinglines.template.csv'
    ],
    'demo_xml': [],
    'installable': True,
    'auto_install': False,
}

