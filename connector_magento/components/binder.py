# -*- coding: utf-8 -*-
# © 2013 Guewen Baconnier,Camptocamp SA,Akretion
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.component.core import Component
from odoo import tools


class MagentoModelBinder(Component):
    """ Bind records and give odoo/magento ids correspondence

    Binding models are models called ``magento.{normal_model}``,
    like ``magento.res.partner`` or ``magento.product.product``.
    They are ``_inherits`` of the normal models and contains
    the Magento ID, the ID of the Magento Backend and the additional
    fields belonging to the Magento instance.
    """
    _name = 'magento.binder'
    _inherit = ['base.binder', 'base.magento.connector']
    _apply_on = [
        'magento.website',
        'magento.store',
        'magento.storeview',
        'magento.res.partner',
        'magento.address',
        'magento.res.partner.category',
        'magento.product.category',
        'magento.product.product',
        'magento.stock.picking',
        'magento.sale.order',
        'magento.sale.order.line',
        'magento.account.invoice',
    ]

    def custom_to_internal(self, external_field, external_id, unwrap=False):
        """ Give the Odoo recordset for an external ID with a custom field

        :param external_field: external field for which we will search
        :param external_id: external ID for which we want
                            the Odoo ID
        :param unwrap: if True, returns the normal record
                       else return the binding record
        :return: a recordset, depending on the value of unwrap,
                 or an empty recordset if the external_id is not mapped
        :rtype: recordset
        """
        if external_field not in self.model._fields.keys():
            if unwrap:
                return self.model.browse()[self._odoo_field]
            return self.model.browse()
        bindings = self.model.with_context(active_test=False).search(
            [(external_field, '=', tools.ustr(external_id)),
             (self._backend_field, '=', self.backend_record.id)]
        )
        if not bindings:
            if unwrap:
                return self.model.browse()[self._odoo_field]
            return self.model.browse()
        bindings.ensure_one()
        if unwrap:
            bindings = bindings[self._odoo_field]
        return bindings
