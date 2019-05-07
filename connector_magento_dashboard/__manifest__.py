# -*- coding: utf-8 -*-
{
    'name': 'Connector Magento - Dashboard',
    'description': """
Connector Magento - Dashboard
===============================================
Adds a Dasboard to Magento Connector with most important Info and Functions
    """,
    'version': '10.0.0.1',
    'category': 'Connector',
    'author': "Callino",
    'website': "http://www.callino.at",
    'depends': [
        'connector_magento'
    ],
    'data': [
        'views/assets_backend.xml',
        'views/actions.xml',
        'views/magento_backend_dashboard.xml',
    ],
    'qweb': [
        "static/src/xml/dashboard.xml",
    ],
    'bootstrap': False,
    'auto_install': False,
}
