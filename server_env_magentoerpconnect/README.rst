.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
    :alt: License: AGPL-3

Server environment for Magento Connector
========================================


This module is based on the `server_environment` module to use files for
configuration.  Thus we can have a different configutation for each
environment (dev, test, staging, prod).  This module define the config
variables for the `magentoerpconnect` module.

In the configuration file, you can configure the url, login and
password of the Magento Backends.

Please refere to `server_environement` documentation for more details


Configuration
=============

To configure this module, you need to add an entry
per environement in the `server_environement_files` module


Usage
=====


Exemple of the section to put in the configuration file::

    [magento_backend.name_of_the_backend]
    location = http://localhost/magento/
    username = my_api_login
    password = my_api_password

Credits
=======

Contributors
------------

* Guewen Baconnier <guewen.baconnier@camptocamp.com>
* Nicolas Bessi <nicolas.bessi@camptocamp.com>

Maintainer
----------

.. image:: https://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: https://odoo-community.org

This module is maintained by the OCA.

OCA, or the Odoo Community Association, is a nonprofit organization whose
mission is to support the collaborative development of Odoo features and
promote its widespread use.

To contribute to this module, please visit http://odoo-community.org.
