# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import Component
from odoo.addons.component_event import skip_if
from odoo.addons.queue_job.job import identity_exact


class MagentoProductAttributeValueBindingExportListener(Component):
    _name = 'magento.product.attribute.value.binding.export.listener'
    _inherit = 'base.connector.listener'
    _apply_on = ['magento.product.attribute.value']

    def on_record_unlink(self, record):
        if not record.backend_id.export_all_options:
            return
        with record.backend_id.work_on(record._name) as work:
            external_id = work.component(usage='binder').to_external(record)
            if external_id:
                record.with_delay(identity_key=identity_exact).export_delete_record(record.backend_id,
                                                         external_id)
