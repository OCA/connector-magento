# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2013 Camptocamp SA
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
    'name': 'Magento Connector Product Tax',
    'version': '0.1',
    'category': 'Connector',
    'description': """
    Map Tax in Import
    """,
    'author': 'Factor Libre S.L.',
    'website': 'http://www.factorlibre.com/',
    'depends': [
        'magentoerpconnect',
        'account',
    ],
    'init_xml': [
    ],
    'update_xml': [
        'account_view.xml',
    ],
    'demo_xml': [

    ],
    'installable': True,
    'active': False,
}
