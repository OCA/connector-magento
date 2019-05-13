# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import Component
from odoo.addons.component_event import skip_if
from odoo.addons.queue_job.job import identity_exact


class MagentoProductMediaBindingExportListener(Component):
    _name = 'magento.product.mdia.binding.export.listener'
    _inherit = 'base.connector.listener'
    _apply_on = ['magento.product.media']

    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    def on_record_create(self, record, fields=None):
        record.with_delay(identity_key=identity_exact).export_record(record.backend_id)

    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    def on_record_write(self, record, fields=None):
        record.with_delay(identity_key=identity_exact).export_record(record.backend_id)

    '''
    TODO: TBD
    def on_record_unlink(self, record):
        with record.backend_id.work_on(record._name) as work:
            external_id = work.component(usage='binder').to_external(record)
            if external_id:
                record.with_delay(identity_key=identity_exact).export_delete_record(record.backend_id,
                                                         external_id)
    '''

class MagentoProductMediaExportListener(Component):
    _name = 'magento.product.media.export.listener'
    _inherit = 'base.connector.listener'
    _apply_on = ['product.product']

    # XXX must check record.env!!!
    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    def on_record_write(self, record, fields=None):
        if 'image' not in fields and 'image_medium' not in fields:
            # We do only update on write on image field
            return
        for binding in record.magento_bind_ids:
            for image_binding in binding.magento_image_bind_ids:
                image_binding.with_delay().export_record(image_binding.backend_id)
