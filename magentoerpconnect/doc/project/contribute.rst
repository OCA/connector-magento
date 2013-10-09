.. _contribute:

#################
Developer's guide
#################

We do accept merge proposals!

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
using the :ref:`installation-guide` or either using our automated Buildout_ recipe.
The manual installation is recommended if you need to add it on an existing
installation or if you want to control your environment in your own manner.

The Buildout_ recipe is an all-in-one package which installs OpenERP, the
connector and provides many facilities for the developers. It includes
developer tools such as:

 * Run the tests on the connector / Magento connector
 * Build the connector / Magento connector documentation
 * Launch the Jobs Workers (for multiprocessing)

So we highly recommend to use this recipe for development.

In order to use it, first get the branch::

    $ bzr branch lp:openerp-connector/7.0-magento-connector-buildout

Then bootstrap it::

    $ python2.6 -S bootstrap.py  # or python, it depends on the distrib

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

.. _Buildout: http://www.buildout.org

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

Run the tests
=============

The Magento Connector and the Connector do not use YAML tests, but only
``unittest2`` tests. The following command lines will run them::

    $ bin/rununittests -m connector
    $ bin/rununittests -m magentoerpconnect

Use the helps for more information about the options::

    $ bin/rununittests --help
    $ bin/rununittests --help-oe

.. note:: There is a known bug which make the tests fails under undetermined
          circumstances (seems related to the initialization of the registry),
          launching again the test suite should work.

Build the documentation
=======================

The documentation uses Sphinx_, use the following lines to build them in HTML::

    $ bin/sphinxbuilder_connector
    $ bin/sphinxbuilder_magentoerpconnect

They will be built in the ``docs`` directory at the root of the buildout.

.. _Sphinx: http://www.sphinx-doc.org

*****************
Magento on the go
*****************

If you want to develop a generic feature on the Magento Connector, we recommend
to use the `ak-magento vagrant box`_.  It installs Magento 1.7 with the demo
data and the Magento part of the Connector.

The project's page describe the installation process, just follow them.

.. _`ak-magento vagrant box`: https://github.com/akretion/ak-magento

***********
How to help
***********

Mailing list
============

The main channel for the discussion is the mailing list, you are invited to
join the team on: https://launchpad.net/~openerp-connector-community and
subscribe to the mailing list.

File an Issue
=============

When you encounter an issue or think there is a bug, you can file a bug on the
project: http://bugs.launchpad.net/magentoerpconnect.

The connector uses several community modules, located in different projects
(``sale_automatic_workflow``, ``sale_exceptions``, ...). If you know which
project is concerned, please report the bug directly on it, in case of doubt,
report it on the Magento Connector project and the developers will eventually
move it to the right project.

Possibly, the bug is related to the connector framework, so you may want to report
it on this project instead: http://bugs.launchpad.net/openerp-connector.

When you report a bug, please give all the sensible information you can provide, such as:

* the reference of the branch of the connector that you are using, and if
  possible the revision numbers of that branch and the dependencies (you can
  use ``bzr revision-info`` for that purpose)

It is very helpful if you can include:

* the detailed steps to reproduce the issue, including any relevant action
* in case of a crash, an extract from the server log files (possibly with a
  few lines before the beginning of the crash report in the log)
* the additionnal modules you use with the connector if it can help

Submit merge proposals for features or fixes
============================================

Merge proposals are much appreciated and we'll take care to review them properly.

The MP process is the following:

1. Get a branch: ``bzr branch lp:magentoerpconnect/7.0 7.0-working-branch``
#. Work on that branch, develop your feature or fix a bug. Please include a test (`Writing tests`_).
#. Ensure that the tests are green (`Run the tests`_)
#. Push that branch on the project ``bzr push lp:~YOURUSER/magentoerpconnect/7.0-my-new-feature``

.. note:: When you push a branch, you can push it on the team
          ``~openerp-connector-community`` instead of your user so anyone in the team is
          able to commit changes / doing corrections.

4. With a browser, go the branch you just pushed and click on the "Propose for merging" link:

    * in the target branch, choose the master branch
    * in the description, put a description which indicates why you made the
      change, ideally with a use case
    * in "extra options", set an appropriate commit message
    * Confirm with the 'Propose Merge' button

.. hint:: You can use the command tools ``bzr lp-propose-merge`` and ``bzr
          lp-open`` instead of a browser for creating the MP.

You can also consult the `Launchpad's documentation on code review`_.

.. _`Launchpad's documentation on code review`: https://help.launchpad.net/Code/Review

Improve the documentation
=========================

Helping on the documentation is extremely valuable and is an easy starting
point to contribute. The documentation is located in the Magento connector's
branch, so you will need to get a branch, working on the documentation and
follow the instructions in the section `Submit merge proposals for features or
fixes`_ to propose your changes.

You are also probably interested in building the documentation, head over `Build the documentation`_.

Translations
============

You may want to translate directly in the ``.po`` files, in such case, follow the
`Submit merge proposals for features or fixes`_ instructions.

The other way is to use the Launchpad's translation system on
https://translations.launchpad.net/magentoerpconnect (maybe not activated as of today)

Writing tests
=============

Every new feature in the connector should have tests. We use exclusively the
``unittest2`` tests with the OpenERP extensions.

See how to `Run the tests`_

The tests are located in ``magentoerpconnect/tests``.

The tests run without any connection to Magento. They mock the API.  In order
to test the connector with representative data, we record real
responses/requests, then use them in the tests. The reference data we use are
those of the Magento demo, which are automatically installed when you install
Magento using theses instructions: `Magento on the go`_.

Thus, in the ``tests`` folder, you will find files with only data, and the
others with the tests.

In order to record, data, you can proceed as follows:

In ``magentoerpconnect/unit/backend_adapter.py`` at line 130,130::

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

Uncomment the line doing a call to ``record()``.
