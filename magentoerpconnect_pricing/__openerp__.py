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

{'name': 'Magento Connector - Pricing',
 'version': '2.0.0',
 'category': 'Connector',
 'depends': ['magentoerpconnect',
             ],
 'author': 'MagentoERPconnect Core Editors',
 'license': 'AGPL-3',
 'website': 'http://www.odoo-magento-connector.com',
 'description': """
Magento Connector - Pricing
===========================

Extension for **Magento Connector**.

The prices of the products are managed in OpenERP using pricelists and
are pushed to Magento.
""",
 'images': [],
 'demo': [],
 'data': ['magento_model_view.xml',
          ],
 'installable': True,
 'application': False,
 }
