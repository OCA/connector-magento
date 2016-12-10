.. _key-questions:


###############################################
Key questions when connecting Odoo with Magento
###############################################

Installing a connector between Odoo and Magento
is not as simple as clicking on the 'Install' button
in the Odoo Apps.

In the e-commerce domain,
there are many use cases
which are strongly domain-specific.
Every website has its own set of specific requirements.
As such, the connector cannot include all the
domain-specific requirements in a generic manner.

This document lists the key questions
you have to answer when connecting your applications.
The questions link to the relevant part in the
documentation when it currently exists.
Some points have no response,
but are things you have to consider and think
before and meanwhile your setup.
You can also consider it as
a checklist for your implementation.

**************
Sale workflows
**************

Payment methods
===============

Are you going to use 'manual' payment types like check or invoices?

Are you going to use 'automatic' payment types like bankcard, paypal,
...?

Each method needs to be configured, follows:
:ref:`configure-payment-methods`.

Automatic workflows
===================

For each `Payment methods`_,
you will want to configure a different workflow,
for instance,
the sales orders of an automatic payment is automatically confirmed.

More details on this configuration in
:ref:`configure-automatic-workflows`.


Exception rules
===============

Do you need to block a sale order according to some conditions?

The connector adds this possibility,
it applies some rules,
for example, it blocks the sale order
if the total amount is different in Odoo and in Magento,
so that is a safe-guard against errors.

You can add your own rules, see :ref:`configure-exception-rules`.


Support and Claims
==================

How will you handle them?

*******
Catalog
*******

Master of data
==============

Where should the data of the products be maintained and edited?

Magento is the master of data:
  Managing the catalog in Magento has the lowest impact on Odoo.
  Much information stay only on Magento
  (product attributes, images, links).
  The categories of products are still imported in Odoo for
  classification.
  However 2 related informations will be updated in Odoo and
  exported to Magento:

  * Available quantity in the stock
  * Price of the products, based on the Odoo pricelists (optionally)

Odoo is the master of data:
  As of today, the handling of the catalog
  in the connector has not been implemented
  (it was in the version for Odoo 6.1).
  It is in the :doc:`/project/roadmap` though.

Types of products
=================

Magento is able to handle many types of products:
simple, configurable, bundle, grouped, virtual, downloadable

Custom options can also be added on the products.

None all of theses types are supported by the connector.
All the product types are planned to be supported
(:doc:`/project/roadmap`).
But, as of today, only simple and configurable products are supported.
Using advanced types of products like bundle will need development,
wether it is generic or specific to your implementation

The custom options would probably be part of a specific development.


*******
Pricing
*******

Taxes included
==============

When you input the prices of your products,
are the taxes included?

Discounts
=========

What kind of discount do you plan do use?
Odoo can't have such advanced discounts as Magento,
so try to keep the things simple here
if you do not want too much specific developments
in your implementation.

Pricing
=======

Do you plan to use multi-currency?

Do you plan to have different prices per websites?
You will need to create different price lists in Odoo.

**********
Accounting
**********

Reconciliations
===============

The connector automatically reconcile the payments
and the invoices entries for the 'automatic' workflows.

However, you will still need to reconcile the bank entries.

You may want to use the reconciliation modules of the
`bank-statement-reconcile`_ project.
They are widely used in production and
are specifically designed for the e-commerce.

.. _`bank-statement-reconcile`: https://github.com/OCA/bank-statement-reconcile


Fiscal Positions
================

Due to the limitations of the Magento API and the intrinsic difference
between Odoo and Magento,
the fiscal positions are not synchronized.
If you need to use fiscal positions,
you may want to use the module
`account_fiscal_position_rules` in the project
`account-fiscal-rule`_.

Note that this configuration will be done
1 time in Magento and 1 time in Odoo.
But once the configuration is done, that works fine.

.. _`account-fiscal-rule`: https://github.com/OCA/account-fiscal-rule


*******************************
Stock, availability, deliveries
*******************************

Shipping methods
================

Which shipping methods will be available?

Configure them using the :ref:`configure-shipping-methods`.

Warehouses
==========

How are you going to organize your warehouses,
do you have several of them?
If you have several Magento Stores,
do you have a warehouse per store
or do they share the same one?

Keep in mind that Magento,
in a standard installation,
does not allow to have different stock quantities
on each store.

Shipping
========

Do you send partial deliveries, or only complete ones?

Replacement of products
=======================

Do you sometimes replace products in the sales orders?
Are you going to modify the sales order on Magento,
or do you want to modify the delivery orders in Odoo?

The latter choice could be complicated because Magento
does not allow to change products in delivery orders.

We recommend to edit the sales orders in Magento, the connector
knows how to handle theses changes.

Tracking and delivery labels
============================

Do you want tracking numbers on your deliveries?

For the printing of your packets' labels,
are you going to use external software
or do you want to print them directly from Odoo?

.. todo:: add a pointer to the modules, I don't have the url actually.

Management of returned goods
============================

How will you manage the returned goods (RMA)? There is nothing out of the box.


*********
Technical
*********

E-mails
=======

Would you want to send e-mails from Magento or from Odoo?
Which transactional e-mails do you plan to send?

Translations
============

Do you need translations for the descriptions of your products?

The language must be configured on the Magento Storeviews in Odoo,
think about it before importing your whole catalog.

Which fields to synchronize
===========================

Think about which fields you have in Magento and you need in Odoo.
You will maybe need to create a customization module
and add the mapping for the new fields,
see :ref:`add-custom-mappings`
