.. _contribute:

#################
Developer's guide
#################

.. contents:: Sections:
   :local:
   :backlinks: top

.. _installation-with-buildout:

********************************************
Connector with batteries included (buildout)
********************************************

Installing the buildout
=======================

When you want to install the Magento connector, you can either install it manually
using the :ref:`installation-guide` or either using our automated Buildout_ config.
The manual installation is recommended if you need to add it on an existing
installation or if you want to control your environment in your own manner.

The Buildout_ config is an all-in-one package which installs Odoo, the
connector and provides many facilities for the developers,
it is based on the `Anybox Buildout Recipe`_.
It includes developer tools such as:

* Run the tests on the connector / Magento connector
* Build the connector / Magento connector documentation
* Launch the Jobs Workers (for multiprocessing)

So we highly recommend to use this configuration for development.

Here are the configuration files https://github.com/guewen/odoo-connector-magento-buildout.

Clone the repo::

    $ git clone https://github.com/guewen/odoo-connector-magento-buildout.git -b 8.0 odoo-connector-magento

and follow the installation steps.

.. warning:: System dependencies to build the eggs: libxml2-dev libxslt1-dev
             that you need to install with apt-get, yum, ...
             You can also use http://pythonhosted.org/anybox.recipe.openerp/first_steps.html#installing-build-dependencies

Head over the next sections to discover the included tools

.. _Buildout: http://www.buildout.org
.. _`Anybox Buildout Recipe`: https://pypi.python.org/pypi/anybox.recipe.openerp

Start Odoo
==========

All the commands are launched from the root directory of the buildout.

In standalone mode (jobs will be threaded)::

    $ bin/start_openerp

With workers (multiprocessing), you need to start dedicated Connector Workers for the jobs::

    $ bin/start_openerp --workers=4
    $ bin/start_connector_worker --workers=2

Start with Supervisord
======================

To start the supervisord daemon, run::

    $ bin/supervisord

The default configuration starts Odoo with 4 workers and 2 Connector
workers. This can be changed in the buildout.cfg file in the ``supervisor`` section.

The services can be managed on::

    $ bin/supervisorctl

Run the tests
=============

The Magento Connector and the Connector framework do not use YAML tests, but only
``unittest2`` tests. The following command lines will run them::

    $ bin/runtests --database db-name -u connector
    $ bin/runtests --database db-name -u magentoerpconnect

Use the help arguments for more information about the options::

    $ bin/runtests --help
    $ bin/runtests --help-oe

Build the documentation
=======================

The documentation uses Sphinx_, use the following lines to build them in HTML::

    $ bin/sphinxbuilder_connector
    $ bin/sphinxbuilder_connector_magento

They will be built in the ``docs`` directory at the root of the buildout.

.. _Sphinx: http://www.sphinx-doc.org

*****************
Magento on Docker
*****************

If you want to develop a generic feature on the Magento Connector, we
recommend to use the `Magento - Odoo Connector docker image`_.  It
installs Magento 1.7 with the sample database and the Magento (PHP) part
of the Connector.

The project's page on Github describe the installation process, just
follow them.

We also use this image as a reference for the data of the tests.

.. _`Magento - Odoo Connector docker image`: https://github.com/guewen/docker-magento

***********
How to help
***********

Mailing list
============

The main channel for the discussion is the mailing list, you are invited to
subscribe on the list named 'Connectors' on: https://odoo-community.org/groups

File an Issue
=============

When you encounter an issue or think there is a bug, you can file a bug on the
project: https://github.com/OCA/connector-magento/issues

The connector uses several community modules, located in different projects
(``sale_automatic_workflow``, ``sale_exceptions``, ...). If you know which
project is concerned, please report the bug directly on it, in case of doubt,
report it on the Magento Connector project and the developers will eventually
move it to the right project.

Possibly, the bug is related to the connector framework, so you may want to report
it on this project instead: https://github.com/OCA/connector/issues.

When you report a bug, please give all the sensible information you can provide, such as:

* the reference of the branch of the connector that you are using, and if
  possible the revision numbers of that branch and the dependencies (you can
  use ``git rev-parse HEAD`` for that purpose)

It is very helpful if you can include:

* the detailed steps to reproduce the issue, including any relevant action
* in case of a crash, an extract from the server log files (possibly with a
  few lines before the beginning of the crash report in the log)
* the additional modules you use with the connector if it can help

Submit Pull Requests for features or fixes
==========================================

Merge proposals are much appreciated and we'll take care to review them properly.

The PR process is the following:

1. Fork the project on https://github.com/OCA/connector-magento
#. Work on your branch, develop a feature or fix a bug. Please include a test (`Writing tests`_).
#. Ensure that the tests are green (`Run the tests`_)
#. Ensure that pep8 is repected
#. Open a Pull Request on GitHub
#. Travis will automatically test pep8 and launch the tests. If Travis fails,
   you will need to correct your branch before it can be merged.

.. note:: Check the `GitHub's help <https://help.github.com/articles/fork-a-repo>`_
          if necessary.


Improve the documentation
=========================

Helping on the documentation is extremely valuable and is an easy starting
point to contribute. The documentation is located in the Magento connector's
project, so you will need to clone the repository, working on the documentation and
follow the instructions in the section `Submit Pull Requests for features or
fixes`_ to propose your changes.

You will also need to read this section: `Build the documentation`_.

Translations
============

Currently the translations should be done directly in the ``.po`` files, follow
the `Submit Pull Requests for features or fixes`_ instructions.

Writing tests
=============

Every new feature in the connector should have tests. We use exclusively the
``unittest2`` tests with the Odoo extensions.

The tests are located in ``magentoerpconnect/tests``.

The tests run without any connection to Magento. They mock the API.  In order
to test the connector with representative data, we record real
responses/requests, then use them in the tests. The reference data we use are
those of the Magento demo, which are automatically installed when you install
Magento using theses instructions: `Magento on Docker`_.

Thus, in the ``tests`` folder, you will find files with only data, and the
others with the tests.

In order to record data, you can proceed as follows:

In ``magentoerpconnect/unit/backend_adapter.py`` at lines 130,130:

.. code-block:: python
   :emphasize-lines: 7,8

    def _call(self, method, arguments):
        try:
            with magentolib.API(self.magento.location,
                                self.magento.username,
                                self.magento.password) as api:
                result = api.call(method, arguments)
                # Uncomment to record requests/responses in ``recorder``
                # record(method, arguments, result)
                _logger.debug("api.call(%s, %s) returned %s",
                              method, arguments, result)
                return result

Uncomment the line doing a call to :py:func:`~openerp.addons.magentoerpconnect.unit.backend_adapter.record()`.
Then, as soon as you will start the server, all the requests and responses
will be stored in global dict. Once you have recorded some exchanges, you can
output them using a tool such as `ERPpeek`_ and by calling the method
:py:class:`~openerp.addons.magentoerpconnect.magento_model.magento_backend.output_recorder`:

.. code-block:: python

    client.MagentoBackend.get(1).output_recorder([])

A path is returned with the location of the file.

When you want to use a set of test data in a test, just use
:py:func:`~openerp.addons.magentoerpconnect.tests.common.mock_api()`:

.. code-block:: python

    from .common import mock_api,
    from .a_data_module import new_set_of_data

    <...>
    def test_new(self):
        <...>
        with mock_api(new_set_of_data):
            # do what the test needs, such as, for instance:
            import_batch(self.session, 'magento.website', backend_id)

See how to `Run the tests`_

Useful links:

* unittest documentation: http://docs.python.org/dev/library/unittest.html
* Odoo's documentation on tests: https://doc.openerp.com/trunk/server/05_test_framework/

.. _`ERPpeek`: https://erppeek.readthedocs.org/en/latest/
