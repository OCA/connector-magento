# -*- coding: utf-8 -*-
# © 2013 Guewen Baconnier,Camptocamp SA,Akretion
# © 2016 Sodexis
# © 2019 Callino
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{'name': 'Magento Connector Custom Attributes',
 'version': '10.0.1.0.0',
 'category': 'Connector',
 'depends': ['connector_magento_product_catalog'],
 'author': "Info a tout prix, MindAndGo, Camptocamp,Akretion,Sodexis,Callino,Odoo Community Association (OCA)",
 'license': 'AGPL-3',
 'website': 'http://www.odoo-magento-connector.com',

 'data': [
     'views/magento_external_objects_menus.xml',
     'views/product_custom_values.xml',
     'views/product_view.xml',
     'views/product_template.xml',
 ],
 'installable': True,
 'application': False,
}
