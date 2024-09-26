# -*- coding: utf-8 -*-
# © 2016 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Magento Connector Product Tax',
    'version': "8.0.1.0.0",
    'category': 'Connector',
    'description': """
    Maps product taxes based on their magento id
    """,
    'author': 'Factor Libre S.L., Odoo Community Association (OCA)',
    'website': 'http://www.factorlibre.com/',
    'license': 'AGPL-3',
    'depends': [
        'magentoerpconnect',
        'account',
    ],
    'data': ['views/account_view.xml'],
    'application': False,
    'installable': True,
}
