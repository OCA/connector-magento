.. Connectors documentation master file, created by
   sphinx-quickstart on Mon Feb  4 11:35:44 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

#########################
Magento OpenERP Connector
#########################

This is a connector linking OpenERP and Magento. It is build on top of
the ``connector`` (TODO: link) framework. It is is structured so that it
can be extended or modified easily as the implementations of
Magento vary a lot.

Features:

* a

* b

* c

Magento OpenERP Connector is mainly developed by the Magentoerpconnect Core
Editors, these being Camptocamp_ and Akretion_. The `source is on
launchpad`_.

.. _Camptocamp: http://www.camptocamp.com
.. _Akretion: http://www.akretion.com
.. _`source is on launchpad`: https://launchpad.net/magentoerpconnect


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
   :maxdepth: 2

   howto/configure_translations
   howto/configure_warehouse
   howto/configure_payment_methods
   howto/configure_automatic_workflows
   howto/configure_exception_rules
   howto/configure_shipping_methods
   howto/configure_emails
   howto/configure_schedulers
   guides/connector_checkpoint
   guides/monitor_resolve_jobs


***************************
Developing on the connector
***************************

Learn about how you can contribute or use the connector as a developer.

Develop
=======

.. toctree::
   :maxdepth: 2

   guides/tutorial_development
   guides/tutorial_customize


API
===

TODO: fixme, not generated due to the openerp.addons namespace

.. toctree::
   :maxdepth: 2

   api/api_connector.rst
   api/api_consumer.rst
   api/api_backend.rst
   api/api_event.rst
   api/api_binder.rst
   api/api_mapper.rst
   api/api_synchronizer.rst
   api/api_backend_adapter.rst
   api/api_queue.rst
   api/api_exception.rst

Project
=======

todo:

* how to contribute

* release notes

* contributors

.. toctree::
   :maxdepth: 2

   project/roadmap


Concepts
========

Glossary:

.. glossary::

    Job

        A unit of work consisting of a single complete and atomic task.
        Example: import of a product.

    Backend

        An external service on which we connect OpenERP. In the context
        of the Magento connector, Magento is a backend.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

