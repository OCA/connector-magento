.. _contribute:

#################
Developer's guide
#################

We do accept merge proposals!


********************************************
Connector with batteries included (buildout)
********************************************

Installing the buildout
=======================

When you want to install the Magento connector, you can install it manually
either using the `Installation Guide`_ or either using our Buildout_ recipe.
The manual installation is recommended if you need to add it on an existing
installation or if you want to control your environment in your own manner.

The Buildout_ recipe is an all-in-one package which installs the connector
and provides many facilities for the developers. It includes developer tools such as:

 * Run the unit tests on the connector / Magento connector
 * Build the connector / Magento connector documentation
 * Launch the Jobs Workers (for multiprocessing)

So we highly recommend to use this recipe for development.

In order to use it, first get the branch::

    $ bzr branch lp:openerp-connector/7.0-magento-connector-buildout

Then bootstrap it::

    $ python2.6 bootstrap.py  # or python, it depends on the distrib

Then run the buildout on the configuration file (eventually change options)::

    $ bin/buildout

If this is is the first time you use it, you'll need to
create a PostgreSQL user whose name is `openerp_magento7` and password is
`openerp_magento7` (according to what you put in the configuration file).
You will also need to create the database.

::

    $ createuser -W openerp_magento7  # then respond to the questions
    $ createdb openerp_magento7 -O openerp_magento7


Head over the next sections to discover the included tools

Start OpenERP
=============

All the commands are run from the root of the buildout.

In standalone mode::

    $ bin/start_openerp

With workers (multiprocessing), you also need to start Connector Workers for the jobs::

    $ bin/start_openerp --workers=4
    $ bin/start_connector_worker --workers=2

Start with Supervisord
======================

To start the supervisord daemon, run::

    $ bin/supervisord

The default configuration is to start OpenERP with 4 workers and 2 Connector
workers. This can be changed in the buildout.cfg file in the ``supervisor`` section.

The services can be managed on::

    $ bin/supervisorctl

Run the unit tests
==================

The Magento Connector and the Connector do not use YAML tests, but only
``unittest2`` tests. The following command lines will run them::

    $ bin/rununittests -m connector
    $ bin/rununittests -m magentoerpconnect

Use the helps for more information about the options::

    $ bin/rununittests --help
    $ bin/rununittests --help-oe

Build the documentation
=======================

The documentation uses Sphinx_, use the following lines to build them in HTML::

    $ bin/sphinxbuilder_connector
    $ bin/sphinxbuilder_magentoerpconnect

They will be built in the ``docs`` directory at the root of the buildout.

.. _Sphinx: http://www.sphinx-doc.org





.. todo:: Complete this page.

          Some topics to cover:

          * mailing list (irc?)
          * bug reports
          * submit merge proposals for features or fixes
          * use and write tests
          * improve documentation
          * translations
