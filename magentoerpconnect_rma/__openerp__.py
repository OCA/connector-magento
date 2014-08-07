# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2013 Camptocamp SA
#    Copyright 2014 Akretion
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

{'name': 'Magentoerpconnect Rma',
 'version': '1.0.0',
 'category': 'Connector',
 'depends': ['magentoerpconnect',
             'crm_claim_rma',
             'document',
             ],
 'author': 'MagentoERPconnect Core Editors',
 'license': 'AGPL-3',
 'description': """
Magento Connector - RMA
=======================================
RMA (Return Merchandise Authorization) importation from Magento
Functionnalities:
    - claims import
    - attachments (from 'claims') synchronisation (import/export)
    - mail messages (from 'claims') synchronisation (import/export) : 'internal notes' are not exported (only mail)

Requirements:
    Magento installation with module 'rma' embeded
 """,
 'data': [
    'magento_model_view.xml',
    'ir_attachment_view.xml',
    'claim_data.xml',
    ],
 'installable': True,
 'application': False,
}
