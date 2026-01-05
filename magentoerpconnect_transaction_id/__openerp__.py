# -*- coding: utf-8 -*-
# Copyright (c) 2015 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    'name': "magentoerpconnect_transaction_id",
    'summary': """
        Map the payment identifier in your sale order""",
    'author': 'ACSONE SA/NV,'
              'Odoo Community Association (OCA)',
    'website': "http://acsone.eu",
    'category': 'Connector',
    'version': '8.0.1.0.0',
    'license': 'AGPL-3',
    'depends': [
        'magentoerpconnect',
        'sale_payment_method',
        'base_transaction_id',
    ],
    'data': [
        'views/payment_method_view.xml',
    ],
}
