# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2014 initOS GmbH & Co. KG (<http://www.initos.com>).
#    Author Katja Matthes <katja.matthes at initos.com>
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
{'name': 'Magentoerpconnect Bundle Import Child Items ',
  'version': '0.1',
  'category': 'Connector',
  'depends': ['magentoerpconnect',
              ],
  'author': 'initOS GmbH & Co. KG',
  'license': 'AGPL-3',
  'description': """
Magento Connector Bundle Items
===============================

* Creates a new connector layer that inherit from version magento1700 (Standard Magento Connector)
* Enable handling of bundle products.
* Import bundle parent item and bundle child items as seperate sale order lines.
* Link the child order lines to the parent line.
 """,
  'data': [ 'sale_view.xml'],
  'installable': True,
  'application': False,
 }
