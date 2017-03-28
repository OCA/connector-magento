# -*- coding: utf-8 -*-
# © 2013 Guewen Baconnier,Camptocamp SA,Akretion
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import openerp.addons.connector.backend as backend


magento = backend.Backend('magento')
""" Generic Magento Backend """

magento1700 = backend.Backend(parent=magento, version='1.7')
""" Magento Backend for version 1.7 """
