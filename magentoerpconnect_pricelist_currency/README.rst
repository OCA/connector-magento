.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

================================================================
Magento Connector - Pricelist in Odoo sale with magento currency
================================================================

This module was created to allow import of magento sales in the same currency that they was in magento sale,
allowing to have the same currency in magento than in Odoo.

Before this module was developed only the default configured price list in Odoo was used,
this behaviour was incorrect if there are many currencies in magento sales,
because of this all the magento sales were imported with the default currency configured in odoo.

Installation
============

Configuration
=============

To configure this module, you need to:

* Create a new **Pricelist Mapping**:

 * Go to *Sales/Configuration/Pricelists/Pricelist Mappings*
 * Create new record:

  * Define a mapping name
  * Select the pricelist that will have this same mapping.
  This field is intended to include same pricelist but with different currencies, but also can be configured with any pricelist with different currencies.

Usage
=====

When a Magento Sale is imported to Odoo will search for mapped price list that match
 the magento sale currency for that sale.

If a price list is found it will change the price list in the created Odoo Sale Order.

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.odoo-community.org/runbot/107/8.0

Known issues / Roadmap
======================


Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/OCA/
connector-magento/issues>`_.
In case of trouble, please check there if your issue has already been reported.
If you spotted it first, help us smashing it by providing a detailed and welcomed feedback `here <https://github.com/OCA/
connector-magento/issues/new?body=module:%20
magentoerpconnect_pricelist_currency%0Aversion:%20
8.0%0A%0A**Steps%20to%20reproduce**%0A-%20...%0A%0A**Current%20behavior**%0A%0A**Expected%20behavior**>`_.


Credits
=======

Contributors
------------

* Hugo Santos <hugo.santos@factorlibre.com>

Maintainer
----------

.. image:: https://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: https://odoo-community.org

This module is maintained by the OCA.

OCA, or the Odoo Community Association, is a nonprofit organization whose
mission is to support the collaborative development of Odoo features and
promote its widespread use.

To contribute to this module, please visit http://odoo-community.org.