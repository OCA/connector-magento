# -*- coding: utf-8 -*-
#
#    Author: Damien Crier
#    Copyright 2015 Camptocamp SA
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
{'name': 'Magento Catalog Simple',
 'version': '8.0.1.0',
 'category': 'Connector',
 'depends': ['magentoerpconnect',
             ],
 'author': "Camptocamp,Odoo Community Association (OCA)",
 'license': 'AGPL-3',
 'website': 'http://www.odoo-magento-connector.com',
 'data': ['views/magento_model_view.xml',
          'views/product_view.xml',
          ],
 'installable': True,
 'application': True,
 }
