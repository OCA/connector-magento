# -*- coding: utf-8 -*-
# © 2013 Guewen Baconnier,Camptocamp SA,Akretion
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{'name': 'Magento Connector Product manager',
 'version': '10.0.1.0.0',
 'category': 'Connector',
 'depends': ['connector_magento',
             ],
 'author': "Info a tout prix, MindAndGo, Camptocamp,Akretion,Sodexis,Odoo Community Association (OCA)",
 'license': 'AGPL-3',
 'website': 'http://www.odoo-magento-connector.com',

 'data': [
        'views/magento_backend_views.xml',
        'views/product_view.xml',
        'views/magento_external_objects_menus.xml',

        
          ],
 'installable': True,
 'application': False,
 } 
