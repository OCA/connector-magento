.. _contribute:

##########
Contribute
##########

We do accept merge proposals!

Connector with batteries included
=================================

When you want to install the Magento connector, you install
it manually (add ref) this is recommanded if you need to add
it on an existing installation or want to control your environment
in your own manner.
Or you can use our all-in-one package. It is based on Buildout_
and includes also many tools such as scripts to

 * Run the unit tests on the connector / Magento connector
 * Build the connector / Magento connector documentation
 * Launch the Jobs Workers (for multiprocessing)

So we highly recommend to use this recipe for development.

In order to use it, first get the branch::

    $ bzr branch lp:openerp-connector/7.0-magento-connector-buildout

Then bootstrap::

    $ python2.6 bootstrap.py  # or python, it depends on the distrib

Eventually adapt `openerp_magento7.cfg`, or create your own
configuration file. Then run the buildout on the configuration file::

    $ bin/buildout -s -c openerp_magento7.cfg

Wait a moment. (todo: add postgres user and db)

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
