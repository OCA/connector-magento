# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import Component


class BaseMagentoConnectorComponent(Component):

    _name = 'base.magento.connector'
    _inherit = 'base.connector'
    _collection = None
    _apply_on = None
    _usage = None
