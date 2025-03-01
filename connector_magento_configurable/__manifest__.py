# -*- coding: utf-8 -*-
# Copyright 2017 Akretion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

{'name': 'Magento Connector - Configurable',
 'version': '10.0.1.0.0',
 'author': 'Akretion, Odoo Community Association (OCA)',
 'license': 'AGPL-3',
 'category': 'Hidden',
 'depends': ['connector_magento'],
 'data': [
     'security/ir.model.access.csv',
     'views/magento_backend_views.xml',
     'views/product_template.xml',
 ],
 'installable': True,
 'auto_install': True,
 }
