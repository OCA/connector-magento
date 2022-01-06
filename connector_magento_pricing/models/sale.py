# -*- coding: utf-8 -*-
# Copyright 2013 Camptocamp SA
# Copyright 2018 Akretion

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping


class SaleOrderImportMapper(Component):
    _inherit = 'magento.sale.order.mapper'

    @mapping
    def pricelist_id(self, record):
        """ Assign to the sale order the price list used on
        the Magento Website or Backend """
        website_binder = self.binder_for('magento.website')
        oe_website_id = website_binder.to_internal(record['website_id'])
        website = self.session.browse('magento.website', oe_website_id)
        if website.pricelist_id:
            pricelist_id = website.pricelist_id.id
        else:
            pricelist_id = self.backend_record.pricelist_id.id
        return {'pricelist_id': pricelist_id}
