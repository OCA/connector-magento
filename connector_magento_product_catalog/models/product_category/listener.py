# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import Component
from odoo.addons.component_event import skip_if
from odoo.addons.queue_job.job import identity_exact


class MagentoProductCategoryBindingExportListener(Component):
    _name = 'magento.product.category.binding.export.listener'
    _inherit = 'base.connector.listener'
    _apply_on = ['magento.product.category']

    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    def on_record_create(self, record, fields=None):
        if self.backend_id.product_synchro_strategy == 'magento_first': 
                return
        record.with_delay(identity_key=identity_exact).export_record(record.backend_id)

    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    def on_record_write(self, record, fields=None):
        if self.backend_id.product_synchro_strategy == 'magento_first': 
                return
        record.with_delay(identity_key=identity_exact).export_record(record.backend_id)

    def on_record_unlink(self, record):
        if self.backend_id.product_synchro_strategy == 'magento_first': 
                return
        with record.backend_id.work_on(record._name) as work:
            external_id = work.component(usage='binder').to_external(record)
            if external_id:
                record.with_delay(identity_key=identity_exact).export_delete_record(record.backend_id,
                                                         external_id)


class MagentoProductCategoryExportListener(Component):
    _name = 'magento.product.category.export.listener'
    _inherit = 'base.connector.listener'
    _apply_on = ['product.category']

    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    def on_record_write(self, record, fields=None):
        for binding in record.magento_bind_ids:
            if binding.backend_id.product_synchro_strategy == 'magento_first': 
                continue
            binding.with_delay(identity_key=identity_exact).export_record(binding.backend_id)

    def on_record_unlink(self, record):
        for binding in record.magento_bind_ids:
            if binding.backend_id.product_synchro_strategy == 'magento_first': 
                continue
            with binding.backend_id.work_on(binding._name) as work:
                external_id = work.component(usage='binder').to_external(binding)
                if external_id:
                    binding.with_delay(identity_key=identity_exact).export_delete_record(binding.backend_id,
                                                                                        external_id)


class MagentoProductCategoryPositionExportListener(Component):
    _name = 'magento.product.position.export.listener'
    _inherit = 'base.connector.listener'
    _apply_on = ['magento.product.position']

    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    def on_record_write(self, record, fields=None):
        record.magento_product_category_id.with_delay(identity_key=('magento_product_category_position_%s'%record.magento_product_category_id.id)).update_positions()
