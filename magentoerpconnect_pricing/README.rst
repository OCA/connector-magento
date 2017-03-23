.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
    :alt: License

Magento Connector - Pricing
===========================

Extension for **Magento Connector**.

Pricelist options are added to the Magento backend and website settings. The
pricelists are used to determine the order currency per website.

By default, the pricelists are also used to manage the prices of the products
in Odoo, pushing them to Magento. You can disable this option in the backend
settings.

Installation
============

This module installs on top of the the **Magento Connector**

Configuration and usage
=======================

Read http://odoo-magento-connector.com/howto/configure_pricing.html

Limitations
===========

The following limitations apply when pushing product prices to Magento:

* The 'Catalog Price Scope' option on Magento must be set to 'Website'
* The prices are exported when they are changed directly on the product,
  not when they are changed on the pricelist (so it works well when the
  pricelists are based on the price filed on the product, such as a
  percent, but does not work when the pricelists have fixed prices)

Credits
=======

Contributors
------------

* Guewen Baconnier <guewen.baconnier@camptocamp.com>

Maintainer
----------

.. image:: http://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: http://odoo-community.org

This module is maintained by the OCA.

OCA, or the Odoo Community Association, is a nonprofit organization
whose mission is to support the collaborative development of Odoo
features and promote its widespread use.

To contribute to this module, please visit http://odoo-community.org.

