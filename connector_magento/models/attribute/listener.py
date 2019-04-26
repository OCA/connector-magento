# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import Component
from odoo.addons.component_event import skip_if
from odoo.addons.queue_job.job import identity_exact


class MagentoProductAttributeBindingExportListener(Component):
    _name = 'magento.product.attribute.binding.export.listener'
    _inherit = 'base.connector.listener'
    _apply_on = ['magento.product.attribute']

    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    def on_record_create(self, record, fields=None):
        if record.backend_id.export_all_options:
            record.with_delay(identity_key=identity_exact).export_record(record.backend_id)

    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    def on_record_write(self, record, fields=None):
        if record.backend_id.export_all_options:
            record.with_delay(identity_key=identity_exact).export_record(record.backend_id)

    def on_record_unlink(self, record):
        if not record.backend_id.export_all_options:
            return
        with record.backend_id.work_on(record._name) as work:
            external_id = work.component(usage='binder').to_external(record)
            if external_id:
                record.with_delay(identity_key=identity_exact).export_delete_record(record.backend_id,
                                                         external_id)


class MagentoProductAttributeExportListener(Component):
    _name = 'magento.product.attribute.export.listener'
    _inherit = 'base.connector.listener'
    _apply_on = ['product.attribute']

    # XXX must check record.env!!!
    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    def on_record_write(self, record, fields=None):
        for binding in record.magento_bind_ids:
            if not binding.backend_id.export_all_options:
                return
            binding.with_delay().export_record(binding.backend_id)
