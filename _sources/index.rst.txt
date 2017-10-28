.. Connectors documentation master file, created by
   sphinx-quickstart on Mon Feb  4 11:35:44 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

######################
Odoo Magento Connector
######################

*Odoo Magento Connector* (also known as *MagentoERPconnect*) is a
bi-directional connector, 100% compatible with the last `Odoo`_ 8.0 and
latest `Magento`_ versions.

Based on the `Odoo Connector`_ framework, this new release of
MagentoERPconnect has been initiated by `Camptocamp`_ and is mainly
developed and maintained by `Camptocamp`_ and `Akretion`_ with several other
:ref:`contributors`.

*Subscribe to the* `project's mailing list (name: Connectors)`_

*Learn how to contribute with the* :ref:`contribute`

*************
Core Features
*************

* **100% Open Source** (`AGPL version 3`_): the full `source code is available
  on GitHub`_
* **Multis**: multi-instances, multi-e-shop, multi-currency,
  multi-warehouse, multi-language
* **Synchronization** of products catalog, customers, sales orders, stock levels,
  shipments, packages' tracking numbers, invoices…
* **Built on top of the** `Odoo Connector`_ **framework with a strong and
  efficient core**: it can then be extended or modified easily from
  separate addons
* **Payment workflow automation**: depending on the mean of payment (credit
  card, wire transfer), possibility to automate workflows in
  Odoo (automatic order validation, automatic invoice validation…).
  For instance, a sales order paid by credit card will automatically
  create an invoice with the "paid" status
* Load testing results: **in a single day, successful import of more
  than 10'000 sales orders** from Magento to Odoo!

.. _`Odoo Connector`: http://www.odoo-connector.com
.. _Camptocamp: http://www.camptocamp.com
.. _Odoo: http://www.odoo.com
.. _Magento: http://www.magento.com
.. _Akretion: http://www.akretion.com
.. _`source code is available on GitHub`: https://github.com/OCA/connector-magento
.. _`AGPL version 3`: http://www.gnu.org/licenses/agpl-3.0.html
.. _`project's mailing list (name: Connectors)`: https://odoo-community.org/groups

********
Workflow
********

.. raw:: html

    <div style="margin-top:10px;">
        <iframe src="http://www.slideshare.net/slideshow/embed_code/27685907" width="427" height="356" frameborder="0" marginwidth="0" marginheight="0" scrolling="no" style="border:1px solid #CCC;border-width:1px 1px 0;margin-bottom:5px" allowfullscreen> </iframe> <div style="margin-bottom:5px"> <strong> <a href="https://fr.slideshare.net/camptocamp/openerp-magento-connector-new-generation-workflow" title="Odoo Magento Connector &quot;New Generation&quot; Workflow" target="_blank">Odoo Magento Connector &quot;New Generation&quot; Workflow</a> </strong> from <strong><a href="http://www.slideshare.net/camptocamp" target="_blank">Camptocamp</a></strong> </div>
    </div>

**************************
Top financial contributors
**************************

.. image:: _static/img/LogicSupply_Orange_260x80_transparent.png
   :alt: Logic Supply
   :target: http://www.logicsupply.com

.. image:: _static/img/logo-debonix.jpg
   :alt: Debonix
   :target: http://www.debonix.fr

|

*See all the project's* :ref:`financial-contributors`.

***********
First steps
***********

.. toctree::
   :maxdepth: 2

   guides/installation_guide
   guides/key_questions


***********************************
Using and configuring the connector
***********************************

Be efficient using and configuring the connector.

.. toctree::
   :maxdepth: 1

   howto/configure_translations
   howto/configure_warehouse
   howto/configure_pricing
   howto/configure_payment_methods
   howto/configure_automatic_workflows
   howto/configure_exception_rules
   howto/configure_shipping_methods
   howto/configure_emails
   howto/configure_schedulers
   howto/configure_taxes
   guides/connector_checkpoint
   guides/monitor_resolve_jobs
   howto/modify_an_order
   howto/faq


***************************
Developing on the connector
***************************

Learn about how you can contribute or use the connector as a developer.

Develop
=======

.. toctree::
   :maxdepth: 3

   project/contribute

Tutorials
=========

.. toctree::
   :maxdepth: 2

   guides/tutorial_development
   guides/tutorial_customize


API
===

General API
-----------

.. toctree::
   :maxdepth: 2

   api/api_connector.rst
   api/api_consumer.rst
   api/api_backend.rst
   api/api_binder.rst
   api/api_synchronizer.rst
   api/api_backend_adapter.rst
   api/api_exception.rst

Models API
----------

.. toctree::
   :maxdepth: 2

   api/api_delivery.rst
   api/api_invoice.rst
   api/api_magento_model.rst
   api/api_partner.rst
   api/api_partner_category.rst
   api/api_product.rst
   api/api_product_category.rst
   api/api_sale.rst
   api/api_stock_picking.rst
   api/api_stock_tracking.rst


*******
Project
*******

.. toctree::
   :maxdepth: 1

   project/roadmap
   project/contributors
   project/changes

******************
Indices and tables
******************

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
