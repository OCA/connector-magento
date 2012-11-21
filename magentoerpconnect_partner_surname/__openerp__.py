# -*- encoding: utf-8 -*-
###############################################################################
#
#   magentoerpconnect_partner_surname for OpenERP
#   Copyright (C) 2012-TODAY Akretion <http://www.akretion.com>.
#     All Rights Reserved
#     @author Sébastien BEAU <sebastien.beau@akretion.com>
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as
#   published by the Free Software Foundation, either version 3 of the
#   License, or (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

{
    'name': 'magentoerpconnect_partner_surname',
    'version': '6.1.0',
    'category': 'Generic Modules/Others',
    'license': 'AGPL-3',
    'description': """
    This module with the dependency base_partner_surname add the 
    posibility to manage the fistname and the last name in a separated field
    instead of having only one field 'name'
    """,
    'author': 'Akretion',
    'website': 'http://www.akretion.com/',
    'depends': ['magentoerpconnect', 'base_partner_surname'], 
    'init_xml': [],
    'update_xml': [ 
           'settings/1.5.0.0/res.partner.address/external.mappinglines.template.csv',
    ],
    'demo_xml': [],
    'installable': True,
    'auto_install': True,
}
