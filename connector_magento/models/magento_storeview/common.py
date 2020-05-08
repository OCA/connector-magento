# Copyright 2103-2019 Camptocamp SA
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging

from datetime import datetime, timedelta
from odoo import models, fields, api
from odoo.addons.component.core import Component
from ..magento_backend.common import IMPORT_DELTA_BUFFER

_logger = logging.getLogger(__name__)


class MagentoStoreview(models.Model):
    _name = 'magento.storeview'
    _inherit = ['magento.binding', 'magento.config.specializer']
    _description = "Magento Storeview"
    _parent_name = 'store_id'

    _order = 'sort_order ASC, id ASC'

    name = fields.Char(required=True, readonly=True)
    code = fields.Char(readonly=True)
    enabled = fields.Boolean(string='Enabled', readonly=True)
    sort_order = fields.Integer(string='Sort Order', readonly=True)
    store_id = fields.Many2one(comodel_name='magento.store',
                               string='Store',
                               ondelete='cascade',
                               readonly=True)
    lang_id = fields.Many2one(comodel_name='res.lang', string='Language')
    team_id = fields.Many2one(comodel_name='crm.team', string='Sales Team')
    base_media_url = fields.Char(
        help=('Base URL to retrieve product images. Used for Magento2 only. '
              'For example: http://magento/media'))
    backend_id = fields.Many2one(
        comodel_name='magento.backend',
        related='store_id.website_id.backend_id',
        string='Magento Backend',
        store=True,
        readonly=True,
        # override 'magento.binding', can't be INSERTed if True:
        required=False,
    )
    import_orders_from_date = fields.Datetime(
        string='Import sale orders from date',
        help='do not consider non-imported sale orders before this date. '
             'Leave empty to import all sale orders',
    )
    no_sales_order_sync = fields.Boolean(
        string='No Sales Order Synchronization',
        help='Check if the storeview is active in Magento '
             'but its sales orders should not be imported.',
    )
    catalog_price_tax_included = fields.Boolean(string='Prices include tax')
    is_multi_company = fields.Boolean(related="backend_id.is_multi_company")

    @api.multi
    def import_sale_orders(self):
        import_start_time = datetime.now()
        for storeview in self:
            if storeview.no_sales_order_sync:
                _logger.debug("The storeview '%s' is active in Magento "
                              "but is configured not to import the "
                              "sales orders", storeview.name)
                continue

            user = storeview.sudo().warehouse_id.company_id.user_tech_id
            if not user:
                user = self.env['res.users'].browse(self.env.uid)

            sale_binding_model = self.env['magento.sale.order']
            if user != self.env.user:
                sale_binding_model = sale_binding_model.sudo(user)

            backend = storeview.sudo(user).backend_id
            if storeview.import_orders_from_date:
                from_string = fields.Datetime.from_string
                from_date = from_string(storeview.import_orders_from_date)
            else:
                from_date = None

            delayable = sale_binding_model.with_delay(priority=1)
            filters = {
                'magento_storeview_id': storeview.external_id,
                'from_date': from_date,
                'to_date': import_start_time,
            }
            delayable.import_batch(backend, filters=filters)
        # Records from Magento are imported based on their `created_at`
        # date.  This date is set on Magento at the beginning of a
        # transaction, so if the import is run between the beginning and
        # the end of a transaction, the import of a record may be
        # missed.  That's why we add a small buffer back in time where
        # the eventually missed records will be retrieved.  This also
        # means that we'll have jobs that import twice the same records,
        # but this is not a big deal because the sales orders will be
        # imported the first time and the jobs will be skipped on the
        # subsequent imports
        next_time = import_start_time - timedelta(seconds=IMPORT_DELTA_BUFFER)
        next_time = fields.Datetime.to_string(next_time)
        self.write({'import_orders_from_date': next_time})
        return True


class StoreviewAdapter(Component):
    _name = 'magento.storeview.adapter'
    _inherit = 'magento.adapter'
    _apply_on = 'magento.storeview'

    _magento_model = 'ol_storeviews'
    _magento2_model = 'store/storeConfigs'
    _admin_path = 'system_store/editStore/store_id/{id}'

    def read(self, external_id, attributes=None):
        """ Conveniently split into two separate APIs in 2.0
        :rtype: dict
        """
        if self.collection.version == '2.0':
            if attributes:
                raise NotImplementedError
            storeview = next(
                record for record in self._call('store/storeViews')
                if record['id'] == external_id)
            storeview.update(next(
                record for record in self._call('store/storeConfigs')
                if record['id'] == external_id))
            return storeview
        return super(StoreviewAdapter, self).read(
            external_id, attributes=attributes)
