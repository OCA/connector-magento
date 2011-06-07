# -*- encoding: utf-8 -*-
##############################################################################
#
#    Author Guewen Baconnier. Copyright Camptocamp SA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name' : 'magento_product_auto_sku',
    'version' : '1.0',
    'depends' : ['base', 'product', 'magentoerpconnect'],
    'author' : 'Camptocamp',
    'description': """Auto incrementation of the Magento SKU column on products""",
    'website': 'http://www.camptocamp.com',
    'init_xml': [],
    'update_xml': ['data.xml', ],
    'demo_xml': [],
    'installable': True,
    'active': False,
}
