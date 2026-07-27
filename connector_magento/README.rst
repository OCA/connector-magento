.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

=================
Magento Connector
=================

This is the new release of the Open-Source connector linking Odoo and
Magento also known under the name of **Magentoerpconnect**.  It is
build on top of the `connector`_ framework. It is structured so that
it can be extended or modified easily from separate addons, a factor of
success when the implementations of Magento vary a lot.

Magento Odoo Connector is part of the Odoo Community Association (OCA).
The `source is on GitHub`_.

This connector is designed to have a strong and efficient core, with the
ability to extend it with extension modules or local customizations.

In other words, the core module contains the minimal scope to run your
e-commerce with Odoo and Magento. More advanced features are
installable using extensions.

It features:

Synchronizations:

* Import the partners and addresses book
* Import the customer groups (becomes partner tags)
* Import the categories of products, with translations
* Import the products, with translations and main image
* Import the sales orders
* Export of the the stock quantities,
  with configuration of the warehouse and an option to choose the stock
  field to use
* Export the delivery orders status
* Export the tracking numbers
* Create the invoices on Magento and get their number back
* Resolve and import the dependencies when they are not yet imported
  (ie. customer, products for sale order)

Automatizations:

* Use the `Automatic workflows` to automatize the workflow of the sales
  according to the payment method (confirm orders, create and reconcile
  payments, ...)
* Per payment method, choose when the orders are imported
  (only when a payment is captured / authorized / always / never)
* Use the `Sales Exceptions` to prevents the processing of sales orders
  with issues

Technical points:

* Built on top of the `connector`_ framework
* Use the `connector_ecommerce`_ addon to share the e-commerce capabilities
  with other e-commerce addons
* Use the jobs system of the `connector`_ framework
* Create `connector`_ checkpoints when new records to verify are imported
* Support Magento 1.7+ and 2.x, the support of earlier versions should be easy to
  add, the `connector`_ framework being designed to handle multiple
  versions with ease.
* Licensed under AGPL version 3
* Designed to be usable with multiple Magento or any other e-commerce backends
  in the same time.


.. _connector: https://github.com/OCA/connector
.. _connector_ecommerce: https://github.com/OCA/connector-ecommerce
.. _`source is on GitHub`: https://github.com/OCA/connector-magento

Installation
============

To install this module, you need to:

Read the full installation guide:
http://odoo-magento-connector.com/guides/installation_guide.html

Configuration and usage
=======================

Read
http://odoo-magento-connector.com/guides/installation_guide.html#after-the-installation

Usage
=====
#. Go to ...

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.odoo-community.org/runbot/107/9.0

Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/OCA/connector-magento/issues>`_. In case of trouble, please
check there if your issue has already been reported. If you spotted it first,
help us smashing it by providing a detailed and welcomed feedback.

Credits
=======

Images
------

* Odoo Community Association: `Icon <https://github.com/OCA/maintainer-tools/blob/master/template/module/static/description/icon.svg>`_.

Contributors
------------

See `contributors' list`_


.. _contributors' list: ./AUTHORS

Maintainer
----------

.. image:: https://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: https://odoo-community.org

This module is maintained by the OCA.

OCA, or the Odoo Community Association, is a nonprofit organization whose
mission is to support the collaborative development of Odoo features and
promote its widespread use.

To contribute to this module, please visit https://odoo-community.org.
