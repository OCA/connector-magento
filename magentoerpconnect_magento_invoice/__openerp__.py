# -*- encoding: utf-8 -*-
###############################################################################
#
#   magentoerpconnect_magento_invoice for OpenERP
#   Copyright (C) 2012-TODAY Akretion <http://www.akretion.com>. All Rights Reserved
#   @author Sébastien BEAU <sebastien.beau@akretion.com>
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
    'name': 'magentoerpconnect_magento_invoice',
    'version': '6.1.1',
    'category': 'Generic Modules',
    'license': 'AGPL-3',
    'description': """This module will use the Magento invoice number for the OpenERP Invoice.
    Be carefull if your Magento is not available you can not validade an invoice in OpenERP
    TODO refactor MagentoERPconnect in order to extract the other way to synchronise order
    """,
    'author': 'Akretion',
    'website': 'http://www.akretion.com/',
    'depends': ['magentoerpconnect'],
    'init_xml': [],
    'update_xml': [
    ],
    'demo_xml': [],
    'installable': True,
    'active': False,
}

