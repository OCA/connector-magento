.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
    :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3

================================
magentoerpconnect_transaction_id
================================

This module let's you define on the payment method the path to a value to use as transaction id into
the informations of a sale order returned as json by magento and map this information into
the transaction_id field defined by OCA/bank-statement-reconcile/base_transaction_id.

The main purpose is to ease the reconciliation process.

Configuration
=============

For each payment method, you can define the path to the transaction_id value in
the informations provided by magento.


Usage
=====

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.odoo-community.org/runbot/107/8.0


Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/OCA/connector-magento/issues>`_.
In case of trouble, please check there if your issue has already been reported.
If you spotted it first, help us smashing it by providing a detailed and welcomed feedback
`here <https://github.com/OCA/connector-magento/issues/new?body=module:%20magentoerpconnect_transaction_id%0Aversion:%208.0%0A%0A**Steps%20to%20reproduce**%0A-%20...%0A%0A**Current%20behavior**%0A%0A**Expected%20behavior**>`_.

Credits
=======

Contributors
------------

* Laurent Mignon <laurent.mignon@acsone.eu>

Maintainer
----------

.. image:: http://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: http://odoo-community.org

This module is maintained by the OCA.

OCA, or the Odoo Community Association, is a nonprofit organization whose mission is to support the collaborative development of Odoo features and promote its widespread use.

To contribute to this module, please visit http://odoo-community.org.
