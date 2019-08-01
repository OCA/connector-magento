# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import Component
from odoo.addons.component_event import skip_if
from odoo.addons.queue_job.job import identity_exact


class MagentoProductProductBindingExportListener(Component):
    _name = 'magento.product.product.binding.export.listener'
    _inherit = 'base.connector.listener'
    _apply_on = ['magento.product.product']

    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    def on_record_create(self, record, fields=None):
        record.with_delay(identity_key=identity_exact).export_record(record.backend_id)

    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    def on_record_write(self, record, fields=None):
        record.with_delay(identity_key=identity_exact).export_record(record.backend_id)

    def on_record_unlink(self, record):
        with record.backend_id.work_on(record._name) as work:
            external_id = work.component(usage='binder').to_external(record)
            if external_id:
                record.with_delay(identity_key=identity_exact).export_delete_record(record.backend_id,
                                                         external_id)


class MagentoProductProductExportListener(Component):
    _name = 'magento.product.product.export.listener'
    _inherit = 'base.connector.listener'
    _apply_on = ['product.product']

    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    def on_record_write(self, record, fields=None):
        if 'image' in fields:
            # We do ignore image field
            del fields['image']
        for binding in record.magento_bind_ids:
            binding.with_delay(identity_key=identity_exact).export_record(binding.backend_id)


class MagentoProductPricelistItemUpdateListener(Component):
    _name = 'magento.product.pricelist.item.listener'
    _inherit = 'base.connector.listener'
    _apply_on = ['product.pricelist.item']

    def update_products(self, record):
        if record.applied_on == '1_product':
            for binding in record.product_tmpl_id.magento_template_bind_ids:
                binding.with_delay(identity_key=identity_exact).export_record(binding.backend_id)
                for variant in record.product_tmpl_id.product_variant_ids:
                    for binding in variant.magento_bind_ids:
                        binding.with_delay(identity_key=identity_exact).export_record(binding.backend_id)
        elif record.applied_on == '0_product_variant':
            for binding in record.product_id.magento_bind_ids:
                binding.with_delay(identity_key=identity_exact).export_record(binding.backend_id)

    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    def on_record_create(self, record, fields=None):
        self.update_products(record)

    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    def on_record_write(self, record, fields=None):
        self.update_products(record)

    def on_record_unlink(self, record):
        self.update_products(record)
