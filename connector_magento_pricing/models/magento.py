# -*- coding: utf-8 -*-
# Copyright 2013 Camptocamp SA
# Copyright 2018 Akretion

from odoo import fields, models, api
from odoo.tools.translate import _


class MagentoBackend(models.Model):
    _inherit = 'magento.backend'

    def get_pricelist_id(self):
        data_obj = self.env['ir.model.data']
        ref = data_obj.get_object_reference('product', 'list0')
        if ref:
            return ref[1]
        return False

    pricelist_id = fields.Many2one(
        'product.pricelist',
        'Pricelist',
        required=True,
        default=get_pricelist_id,
        help='The price list used to define '
             'the prices of the products in '
             'Magento.')

    @api.onchange('pricelist_id')
    def onchange_pricelist_id(self):
        if not self.id:  # new record
            return {}
        warning = {
            'title': _('Warning'),
            'message': _('If you change the pricelist of the backend, '
                         'the price of all the products will be updated '
                         'in Magento.')
        }
        return {'warning': warning}

    def _update_default_prices(self):
        """ Update the default prices of the products linked with
        this backend.

        The default prices are linked with the 'Admin' website (id: 0).
        """
        websites = self.env['magento.website'].search([
            ('backend_id', 'in'),
            ('external_id', '=', '0')])
        websites._update_all_prices()

    def write(self, vals):
        if 'pricelist_id' in vals:
            self._update_default_prices()
        return super(MagentoBackend, self).write(vals)


class MagentoWebsite(models.Model):
    _inherit = 'magento.website'

    pricelist_id = fields.Many2one(
        'product.pricelist',
        'Pricelist',
        help='The pricelist used to define '
             'the prices of the products in '
             'Magento for this website.\n'
             'Choose a pricelist only if the '
             'prices are different for this '
             'website.\n'
             'When empty, the default price '
             'will be used.')

    def _update_all_prices(self):
        """ Update the prices of all the products linked to the
        website. """
        for website in self:
            if website.external_id == '0':
                # 'Admin' website -> default values
                # Update the default prices on all the products.
                binding_ids = website.backend_id.product_binding_ids
            else:
                binding_ids = website.product_binding_ids
            for binding in binding_ids:
                binding.with_delay().export_product_price(
                    website_id=website.id)
                break
        return True

    @api.onchange('pricelist_id')
    def onchange_pricelist_id(self):
        if not self.id:  # new record
            return {}
        warning = {
            'title': _('Warning'),
            'message': _('If you change the pricelist of the website, '
                         'the price of all the products linked with this '
                         'website will be updated in Magento.')
        }
        return {'warning': warning}

    def write(self, vals):
        if 'pricelist_id' in vals:
            self._update_all_prices()
        return super(MagentoWebsite, self).write(vals)
