# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import Component


class PartnerDeleter(Component):
    """ Partner deleter for Magento """
    _name = 'magento.partner.exporter.deleter'
    _inherit = 'magento.exporter.deleter'
    _apply_on = ['magento.res.partner', 'magento.address']
