# -*- coding: utf-8 -*-
# Copyright (c) 2015 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    'name': "magentoerpconnect_transaction_id",
    'summary': """
        Map the payment identifier in your sale order""",
    'author': 'ACSONE SA/NV,'
              'Odoo Community Association (OCA)',
    'website': 'https://github.com/OCA/connector-magento',
    'category': 'Connector',
    'version': '10.0.1.0.0',
    'license': 'AGPL-3',
    'depends': [
        'component',
        'connector',
        'connector_magento',
        'account_payment_mode',
        'base_transaction_id',
        'sale_automatic_workflow_payment_ref',
    ],
    'data': [
        'views/account_payment_mode.xml',
    ],
}
