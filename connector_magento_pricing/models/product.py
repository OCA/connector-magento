# -*- coding: utf-8 -*-
# Copyright 2013 Camptocamp SA
# Copyright 2018 Akretion


from odoo import api, models
from odoo.tools.translate import _
from odoo.addons.queue_job.job import job, related_action
from odoo.addons.queue_job.exception import JobError
from odoo.addons.component.core import Component
from odoo.addons.component_event import skip_if
from odoo.addons.connector.components.mapper import mapping, only_create


# TODO: replace a price mapper only, not the full mapper
class ProductImportMapper(Component):
    _inherit = 'magento.product.product.import.mapper'

    @only_create
    @mapping
    def price(self, record):
        """ The price is imported at the creation of
        the product, then it is only modified and exported
        from Odoo """
        return super(ProductImportMapper, self).price(record)


class ProductPriceExporter(Component):
    """ Export the price of a product.

    Use the pricelist configured on the backend for the
    default price in Magento.
    If different pricelists have been configured on the websites,
    update the prices on the different websites.
    """
    _name = 'magento.product.price.exporter'
    _inherit = 'base.exporter'
    _usage = 'price.exporter'
    _apply_on = 'magento.product.product'

    def _get_price(self, pricelist_id):
        """ Return the raw Odoo data for ``self.binding_id`` """
        if pricelist_id is None:
            # a False value will set the 'Use default value' in Magento
            return False
        return self.env[self._apply_on].with_context(
            {'pricelist': pricelist_id}).browse(self.binding_id.id).price

    def _update(self, data, storeview_id=None):
        self.backend_adapter.write(self.binding_id.external_id, data,
                                   storeview_id=storeview_id)

    def _run(self, binding, website_id=None):
        """ Export the product inventory to Magento

        :param website_id: if None, export on all websites,
                           or Odoo ID for the website to update
        """
        # export of products is not implemented so we just raise
        # if the export was existing, we would export it
        assert binding.external_id, "Record has been deleted in Magento"
        pricelist = binding.backend_id.pricelist_id
        if not pricelist:
            name = binding.backend_id.name
            raise JobError.IDMissingInBackend(
                'Configuration Error:\n'
                'No pricelist configured on the backend %s.\n\n'
                'Resolution:\n'
                'Go to Connectors > Backends > %s.\n'
                'Choose a pricelist.' % (name, name))
        pricelist_id = pricelist.id

        # export the price for websites if they have a different
        # pricelist
        storeview_binder = self.binder_for('magento.storeview')
        for website in binding.backend_id.website_ids:
            if website_id is not None and website.id != website_id:
                continue
            # 0 is the admin website, the update on this website
            # set the default values in Magento, we use the default
            # pricelist
            site_pricelist_id = None
            if website.external_id == '0':
                site_pricelist_id = pricelist_id
            elif website.pricelist_id:
                site_pricelist_id = website.pricelist_id.id

            # The update of the prices in Magento is very weird:
            # - The price is different per website (if the option
            #   is active in the config), but is shared between
            #   the store views of a website.
            # - BUT the Magento API expects a storeview id to modify
            #   a price on a website (and not a website id...)
            # So we take the first storeview of the website to update.
            storeview_ids = self.env['magento.storeview'].search(
                [('store_id.website_id.id', '=', website.id)]).ids
            if not storeview_ids:
                continue
            magento_storeview = storeview_binder.to_internal(storeview_ids[0])
            self.binding_id = binding
            price = self._get_price(site_pricelist_id)
            self._update({'price': price}, storeview_id=magento_storeview.id)
        self.binder.bind(binding.external_id, binding.id)
        return _('Prices have been updated.')


class MagentoProductProduct(models.Model):
    _inherit = 'magento.product.product'

    @job(default_channel='root.magento')
    @related_action(action='related_action_unwrap_binding')
    @api.multi
    def export_product_price(self, website_id=None):
        """ Export the price of a product. """
        self.ensure_one()
        with self.backend_id.work_on(self._name) as work:
            price_exporter = work.component(usage='price.exporter')
            return price_exporter._run(self, website_id=website_id)


class MagentoProductPriceListener(Component):
    _name = 'product.product.listener'
    _inherit = 'base.event.listener'
    _apply_on = ['product.product']

    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    def on_product_price_changed(self, record):
        """ When a product.product price has been changed """
        for binding in record.magento_bind_ids:
            binding.with_delay(priority=5).export_product_price()
