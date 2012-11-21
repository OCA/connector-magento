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


{'name': 'Magentoerpconnect Payment',
 'version': '6.1.0',
 'category': 'Generic Modules',
 'author': "Camptocamp",
 'license': 'AGPL-3',
 'description': """Module to extend the module magentoerpconnect.

It aims to ease the workflow of the payments for the sale orders done on Magento.
Actually, there is mainly, without deep into details, 2 workflows:
1. (Pre)-Payments done on Magento (credit card, paypal, ...) with a "need to update" flag.
2. Payments by cheque or bank, for which we wait a payment, before treat the order with a standard / manual workflow (bank statement / voucher, ...).

With Magentoerpconnect, the pre-payments are fully automatic, OpenERP wait until the payment is done on Magento, then manage its sale order workflow
(prepaid, postpaid, ...), create and auto-reconcile the payment with the invoice.

It's a mess that the payment done by cheque or other "unsure" payment does not benefit from a so advanced workflow,
because we also have all the data to automatically create payments and reconcile them.

So, this module adds a button "Magento Payment" to create the payment on Magento once you've received your payment.
This button also update your order ("need to update") and let it continues its workflow as defined in its Base Sale Payment Type
exactly as it was a pre-payment.

This allow to have one and only one Magento -> OpenERP payment worlflow.

""",
 'images': ['images/magentocoreeditors.png',
            'images/magentoerpconnect.png', ],
 'website': "https://launchpad.net/magentoerpconnect",
 'depends': ['magentoerpconnect',
             'sale',
             'sale_exceptions'],
 'init_xml': [],
 'update_xml': ['sale_view.xml',
                'invoice_view.xml',
                'payment_type_view.xml'],
 'demo_xml': [],
 'installable': True,
 'auto_install': False
}
