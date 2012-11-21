# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2012 Camptocamp SA
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

{
    'name': 'Magentoerpconnect Partner Fiscal Category',
    'version': '6.1.0',
    'category': 'Generic Modules',
    "author" : "Camptocamp",
    'license': 'AGPL-3',
    'description': """

Link module between :
 - Magentoerpconnect
 - account_fiscal_rules_partner_category


Maps the Fiscal Category on the Partners with the Customer Group of Magento

It can thereby be used in fiscal position rules.

account_fiscal_rules_partner_category module can be found
in lp:c2c-financial-addons branch

""",
    'images': ['images/magentocoreeditors.png',
               'images/magentoerpconnect.png', ],
    "website" : 'https://launchpad.net/magentoerpconnect',
    'depends': ['magentoerpconnect',
                'account_fiscal_rules_partner_category', ],
    'init_xml': [],
    'update_xml': [#'settings/1.3.2.4/external.mappinglines.template.csv',
                   'settings/1.5.0.0/external.mappinglines.template.csv', ],
    'demo_xml': [],
    'installable': True,
    'auto_install': True,
}
