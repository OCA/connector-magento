# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.tools.translate import _
from odoo.addons.component.core import Component


class MagentoProductAttributeValueDeleter(Component):
    """ Base deleter for Magento """
    _name = 'magento.product.attribute.value.deleter'
    _inherit = 'magento.exporter.deleter'
    _apply_on = ['magento.product.attribute.value']

    def run(self, external_id):
        """ Run the synchronization, delete the record on Magento

        :param external_id: identifier of the record to delete
        """
        # External_id is attribute_id + _ + value from magento - we do only need the value here
        magento_attribute_id = external_id.split('_')[0]
        magento_value_id = external_id.split('_')[1]
        self.backend_adapter.delete(magento_value_id, magento_attribute_id)
        return _('Record %s deleted on Magento') % (magento_value_id,)
