.. _contribute:

#################
Developer's guide
#################

.. _installation-dev-env:

***************
Dev Environment
***************

Installing the dev environment with Docker
==========================================

When you want to install the Magento connector, you can either install it manually
using the :ref:`installation-guide` or either using our Docker config.
The manual installation is recommended if you need to add it on an existing
installation or if you want to control your environment in your own manner.

The Docker config is an all-in-one package which installs Odoo, the
connector, Magento and provides niceties for the developers.

It includes developer tools such as:

* Run the tests on the connector / Magento connector
* Build the connector / Magento connector documentation
* Launch the Jobs Workers (for multiprocessing)

The dev environment is on: https://github.com/guewen/odoo-magento-connector-workspace

Clone the repo::

    $ git clone https://github.com/guewen/odoo-magento-connector-workspace/ -b 10.0

and follow the installation steps described in the README of the project..

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
#. Ensure that the tests are green
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

Translations
============

Currently the translations should be done directly in the ``.po`` files, follow
the `Submit Pull Requests for features or fixes`_ instructions.

Writing tests
=============

Every new feature in the connector should have tests. We use exclusively the
``unittest2`` tests with the Odoo extensions.

The tests are located in ``connector_magento/tests``.

The tests run without any connection to Magento. They use `vcr.py
<https://vcrpy.readthedocs.io/en/latest/>`_ in order to record real requests
made towards the Magento API.  The first time a test is run, vrcpy runs the
request on a real Magento, the next times the test is run, it uses the
registered data.
The reference data we use are those of the Magento demo data.



.. code-block:: python

    from .common import mock_api,
    from .a_data_module import new_set_of_data

    <...>
    def test_new(self):
        <...>
        with recorder.use_cassette(
                'test_export_xxx') as cassette:
            # do what the test needs, such as, for instance:
            binding.export_record()
            # all http calls are recorded in 'cassette'
            # we can now check many things in the cassette itself
            self.assertEqual(1, len(cassette.requests))

Useful links:

* unittest documentation: https://docs.python.org/2/library/unittest.html
* Odoo's documentation on tests: https://www.odoo.com/documentation/10.0/reference/testing.html
* vcr.py documentation: https://vcrpy.readthedocs.io/en/latest/
* pytest odoo plugin: https://pypi.python.org/pypi/pytest-odoo
