.. _contribute:

##########
Contribute
##########

We do accept merge proposals!

Connector with batteries included
=================================

When you want to install the Magento connector, you can install
it manually (add ref) or using our Buildout_ recipe.
The manual installation is recommanded if you need to add it on an existing
installation or if you want to control your environment in your own manner.
The Buildout_ recipe is a all-in-one package which installs the connector
and provides many facilities for the developers. It includes developer tools such as

 * Run the unit tests on the connector / Magento connector
 * Build the connector / Magento connector documentation
 * Launch the Jobs Workers (for multiprocessing)

So we highly recommend to use this recipe for development.

In order to use it, first get the branch::

    $ bzr branch lp:openerp-connector/7.0-magento-connector-buildout

Then bootstrap it::

    $ python2.6 bootstrap.py  # or python, it depends on the distrib

Eventually adapt `openerp_magento7.cfg`, or create your own
configuration file. Then run the buildout on the configuration file::

    $ bin/buildout -s -c openerp_magento7.cfg

Wait a moment.

If this is is the first time you use it, you'll need to
create a PostgreSQL user whose name is `openerp_magento7` and password is
`openerp_magento7` (according to what you put in the configuration file).
You will also need to create the database.

::
    $ createuser -W openerp_magento7  # then respond to the questions
    $ createdb openerp_magento7 -O openerp_magento7


Head over the next sections to discover the included tools
 - start openerp
 - start with supervisord
 - start jobs worker
 - unit test
 - build the doc









.. todo:: Complete this page.

          Some topics to cover:

          * mailing list (irc?)
          * bug reports
          * submit merge proposals for features or fixes
          * use and write tests
          * improve documentation
          * translations
