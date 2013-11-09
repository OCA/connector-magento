# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2013 Camptocamp SA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


from openerp.tools.translate import _
from openerp.addons.connector.queue.job import job
from openerp.addons.connector.exception import FailedJobError
from openerp.addons.connector.unit.mapper import (mapping,
                                                  only_create
                                                  )
from openerp.addons.connector_ecommerce.event import on_product_price_changed
from openerp.addons.magentoerpconnect.unit.export_synchronizer import (
    MagentoBaseExporter)
from openerp.addons.magentoerpconnect.backend import magento
from openerp.addons.magentoerpconnect import product
from openerp.addons.magentoerpconnect.connector import get_environment


@magento(replacing=product.ProductImportMapper)
class ProductImportMapper(product.ProductImportMapper):
    _model_name = 'magento.product.product'

    @only_create
    @mapping
    def price(self, record):
        """ The price is imported at the creation of
        the product, then it is only modified and exported
        from OpenERP """
        return super(ProductImportMapper, self).price(record)


@magento
class ProductPriceExporter(MagentoBaseExporter):
    """ Export the price of a product.

    Use the pricelist configured on the backend for the
    default price in Magento.
    If different pricelists have been configured on the websites,
    update the prices on the different websites.
    """
    _model_name = ['magento.product.product']

    def _get_price(self, pricelist_id):
        """ Return the raw OpenERP data for ``self.binding_id`` """
        if pricelist_id is None:
            return False  # a False value will set the 'Use default value'
                          # in Magento
        with self.session.change_context({'pricelist': pricelist_id}):
            return self.session.read(self.model._name,
                                     self.binding_id,
                                     ['price'])['price']

    def _update(self, data, storeview_id=None):
        self.backend_adapter.write(self.magento_id, data,
                                   storeview_id=storeview_id)

    def _run(self, website_id=None):
        """ Export the product inventory to Magento

        :param website_id: if None, export on all websites,
                           or OpenERP ID for the website to update
        """
        # export of products is not implemented so we just raise
        # if the export was existing, we would export it
        assert self.magento_id, "Record has been deleted in Magento"
        pricelist = self.backend_record.pricelist_id
        if not pricelist:
            name = self.backend_record.name
            raise FailedJobError(
                'Configuration Error:\n'
                'No pricelist configured on the backend %s.\n\n'
                'Resolution:\n'
                'Go to Connectors > Backends > %s.\n'
                'Choose a pricelist.' % (name, name))
        pricelist_id = pricelist.id

        # export the price for websites if they have a different
        # pricelist
        storeview_binder = self.get_binder_for_model('magento.storeview')
        for website in self.backend_record.website_ids:
            if website_id is not None and website.id != website_id:
                continue
            # 0 is the admin website, the update on this website
            # set the default values in Magento, we use the default
            # pricelist
            site_pricelist_id = None
            if website.magento_id == '0':
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
            storeview_ids = self.session.search(
                'magento.storeview',
                [('store_id.website_id', '=', website.id)])
            if not storeview_ids:
                continue
            magento_storeview = storeview_binder.to_backend(storeview_ids[0])
            price = self._get_price(site_pricelist_id)
            self._update({'price': price}, storeview_id=magento_storeview)
        self.binder.bind(self.magento_id, self.binding_id)
        return _('Prices have been updated.')


@on_product_price_changed
def product_price_changed(session, model_name, record_id, fields=None):
    """ When a product.product price has been changed """
    if session.context.get('connector_no_export'):
        return
    model = session.pool.get(model_name)
    record = model.browse(session.cr, session.uid,
                          record_id, context=session.context)
    for binding in record.magento_bind_ids:
        export_product_price.delay(session,
                                   binding._model._name,
                                   binding.id,
                                   priority=5)


@job
def export_product_price(session, model_name, record_id, website_id=None):
    """ Export the price of a product. """
    product_bind = session.browse(model_name, record_id)
    backend_id = product_bind.backend_id.id
    env = get_environment(session, model_name, backend_id)
    price_exporter = env.get_connector_unit(ProductPriceExporter)
    return price_exporter.run(record_id, website_id=website_id)
