# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import AbstractComponent


class BaseMagentoConnectorComponent(AbstractComponent):
    """ Base Magento Connector Component

    All components of this connector should inherit from it.
    """

    _name = 'base.magento.connector'
    _inherit = 'base.connector'
    _collection = 'magento.backend'
