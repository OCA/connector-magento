# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2013 Camptocamp SA
#    Copyright 2013 Akretion
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

{'name': 'Magento Connector',
 'version': '8.0.3.0.0',
 'category': 'Connector',
 'depends': ['account',
             'product',
             'delivery',
             'sale_stock',
             'connector_ecommerce',
             'product_m2mcategories',
             ],
 'external_dependencies': {
     'python': ['magento'],
 },
 'author': "Camptocamp,Akretion,Odoo Community Association (OCA)",
 'license': 'AGPL-3',
 'website': 'http://www.odoo-magento-connector.com',
 'images': ['images/magento_backend.png',
            'images/jobs.png',
            'images/product_binding.png',
            'images/invoice_binding.png',
            'images/magentoerpconnect.png',
            ],
 'demo': [],
 'data': ['setting_view.xml',
          'magentoerpconnect_data.xml',
          'magento_model_view.xml',
          'product_view.xml',
          'partner_view.xml',
          'sale_view.xml',
          'invoice_view.xml',
          'magentoerpconnect_menu.xml',
          'delivery_view.xml',
          'stock_view.xml',
          'security/ir.model.access.csv',
          'payment_method_view.xml',
          ],
 'installable': True,
 'application': True,
 }
