# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2014 Camptocamp SA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{'name': 'Server environment for Magento Connector',
 'version': '1.0',
 'author': "Camptocamp,Odoo Community Association (OCA)",
 'maintainer': 'Camptocamp',
 'license': 'AGPL-3',
 'category': 'Tools',
 'complexity': 'expert',
 'depends': ['base',
             'server_environment',
             'magentoerpconnect',
             ],
 'description': """
Server environment for Magento Connector
========================================

This module is based on the `server_environment` module to use files for
configuration.  Thus we can have a different configutation for each
environment (dev, test, staging, prod).  This module define the config
variables for the `magentoerpconnect` module.

In the configuration file, you can configure the url, login and
password of the Magento Backends.

Exemple of the section to put in the configuration file::

    [magento_backend.name_of_the_backend]
    location = http://localhost/magento/
    username = my_api_login
    password = my_api_password

""",
 'website': 'http://www.camptocamp.com',
 'data': [],
 'test': [],
 'installable': True,
 'auto_install': False,
 }
