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
 'version': '2.5.0',
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
 'author': 'Connector Core Editors',
 'license': 'AGPL-3',
 'website': 'http://www.odoo-magento-connector.com',
 'description': """
Magento Connector
=================

This is the new release of the Open-Source connector linking OpenERP and
Magento also known under the name of **Magentoerpconnect**.  It is
build on top of the `connector`_ framework. It is is structured so that
it can be extended or modified easily from separate addons, a factor of
success when the implementations of Magento vary a lot.

Magento OpenERP Connector is mainly developed by the Connector Core
Editors, these being Camptocamp_ and Akretion_. The `source is on
GitHub`_.

This connector is designed to have a strong and efficient core, with the
ability to extend it with extension modules or local customizations.

In other words, the core module contains the minimal scope to run your
e-commerce with OpenERP and Magento. More advanced features are
installable using extensions.

It features:

Synchronizations:

* Import the partners and addresses book
* Import the customer groups (becomes partner tags)
* Import the categories of products, with translations
* Import the products, with translations and main image
* Import the sales orders
* Update the the stock quantities,
  with configuration of the warehouse and stock field to use
* Export the delivery orders
* Export the tracking numbers
* Create the invoices on Magento and get their number back
* Import the dependencies when they are not yet imported
  (ie. customer, products for sale order)

Automatizations:

* Use the `Automatic workflows` to automatize the workflow of the sales
  according to the payment method (confirm orders, create and reconcile
  payments, ...)
* Per payment method, choose when the orders are imported
  (only when a payment is received, always, never)
* Use the `Sales Exceptions` to prevents the processing of sales orders
  with issues

Technical points:

* Built on top of the `connector`_ framework
* Use the `connector_ecommerce`_ addon to share the e-commerce capabilities
  with other e-commerce addons
* Use the jobs system of the `connector`_ framework
* Create `connector`_ checkpoints when new records to verify are imported
* Support Magento 1.7, the support of earlier versions should be easy to
  add, the `connector`_ framework being designed to handle multiple
  versions with ease.
* Licensed under AGPL version 3
* Designed to be usable with multiple Magento or any other e-commerce backends
  in the same time.

Available extensions:

* Pricing
        allows to manage the prices in OpenERP using pricelists,
        prices are update to Magento when changed
* Export of partners (Experimental)
        Export new partners on Magento, not complete.


.. _connector: https://github.com/OCA/connector
.. _connector_ecommerce: https://github.com/OCA/connector-ecommerce
.. _Camptocamp: http://www.camptocamp.com
.. _Akretion: http://www.akretion.com
.. _`source is on GitHub`: https://github.com/OCA/connector-magento

""",
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
          'payment_invoice.xml',
          ],
 'installable': True,
 'application': True,
 }
