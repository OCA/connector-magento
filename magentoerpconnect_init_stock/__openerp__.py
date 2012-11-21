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

{'name' : 'Magentoerpconnect Initialize Stock',
 'version' : '6.1.0',
 'author' : 'Camptocamp',
 'maintainer': 'Camptocamp',
 'license': 'AGPL-3',
 'category': 'Generic Modules',
 'complexity': "easy",
 'depends' : ['magentoerpconnect'],
 'description': """
Simple module to add update the stock inventory values and configuration on
Magento right after a product is created on Magento.

Warning: this needs more resources and on an export of the catalog,
the stock inventory update for new products will be done twice.

The benefits is that the new created products have the correct
configuration directly.
 """,
 'website': 'http://www.camptocamp.com',
 'init_xml': [],
 'update_xml': [],
 'demo_xml': [],
 'tests': [],
 'installable': True,
 'auto_install': False,
}
