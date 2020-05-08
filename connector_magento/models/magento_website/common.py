# © 2013-2019 Guewen Baconnier,Camptocamp SA,Akretion
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from datetime import datetime, timedelta
from odoo import models, fields, api
from odoo.addons.component.core import Component
from ..magento_backend.common import IMPORT_DELTA_BUFFER


class MagentoWebsite(models.Model):
    _name = 'magento.website'
    _inherit = ['magento.binding', 'magento.config.specializer']
    _description = 'Magento Website'
    _parent_name = 'backend_id'

    _order = 'sort_order ASC, id ASC'

    name = fields.Char(required=True, readonly=True)
    code = fields.Char(readonly=True)
    sort_order = fields.Integer(string='Sort Order', readonly=True)
    store_ids = fields.One2many(
        comodel_name='magento.store',
        inverse_name='website_id',
        string='Stores',
        readonly=True,
    )
    import_partners_from_date = fields.Datetime(
        string='Import partners from date',
    )
    product_binding_ids = fields.Many2many(
        comodel_name='magento.product.product',
        string='Magento Products',
        readonly=True,
    )
    is_multi_company = fields.Boolean(related="backend_id.is_multi_company")

    @api.multi
    def import_partners(self):
        import_start_time = datetime.now()
        for website in self:
            backend = website.backend_id
            if website.import_partners_from_date:
                from_string = fields.Datetime.from_string
                from_date = from_string(website.import_partners_from_date)
            else:
                from_date = None
            self.env['magento.res.partner'].with_delay().import_batch(
                backend,
                filters={'magento_website_id': website.external_id,
                         'from_date': from_date,
                         'to_date': import_start_time}
            )
        # Records from Magento are imported based on their `created_at`
        # date.  This date is set on Magento at the beginning of a
        # transaction, so if the import is run between the beginning and
        # the end of a transaction, the import of a record may be
        # missed.  That's why we add a small buffer back in time where
        # the eventually missed records will be retrieved.  This also
        # means that we'll have jobs that import twice the same records,
        # but this is not a big deal because they will be skipped when
        # the last `sync_date` is the same.
        next_time = import_start_time - timedelta(seconds=IMPORT_DELTA_BUFFER)
        next_time = fields.Datetime.to_string(next_time)
        self.write({'import_partners_from_date': next_time})
        return True


class WebsiteAdapter(Component):
    _name = 'magento.website.adapter'
    _inherit = 'magento.adapter'
    _apply_on = 'magento.website'

    _magento_model = 'ol_websites'
    _magento2_model = 'store/websites'
    _admin_path = 'system_store/editWebsite/website_id/{id}'
    # Magento2 url does not seem to be valid without session key
    # and disabling it is not recommended due to security concerns
    # _admin2_path = 'admin/system_store/editWebsite/website_id/{id}'
