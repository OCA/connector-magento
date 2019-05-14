# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import Component
from odoo.addons.component_event import skip_if
from odoo.addons.queue_job.job import identity_exact


class MagentoProductProductExportListener(Component):
    _inherit = 'magento.product.product.export.listener'

    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    def on_record_write(self, record, fields=None):
        for binding in record.magento_bind_ids:
            # First - do update the custom attribute values
            for key in record:
                binding.check_field_mapping(key, record)
        super(MagentoProductProductExportListener, self).on_record_write(record, fields)
