# -*- coding: utf-8 -*-
# Copyright 2019 Callino
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.tools.translate import _
from odoo.addons.component.core import Component


class ProductCategoryDefinitionDeleter(Component):
    """ Base deleter for Magento """
    _name = 'magento.product.category.deleter'
    _inherit = 'magento.exporter.deleter'
    _apply_on = ['magento.product.category']

    def run(self, external_id):
        """ Run the synchronization, delete the record on Magento

        :param external_id: identifier of the record to delete
        """
        self.backend_adapter.delete(external_id)
        return _('Record %s deleted on Magento') % (external_id,)
