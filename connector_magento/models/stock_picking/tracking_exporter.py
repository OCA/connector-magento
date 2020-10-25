# Copyright 2013-2019 Camptocamp SA
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from odoo import _
from odoo.addons.queue_job.exception import FailedJobError
from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class MagentoTrackingExporter(Component):
    _name = 'magento.stock.tracking.exporter'
    _inherit = 'magento.exporter'
    _apply_on = ['magento.stock.picking']
    _usage = 'tracking.exporter'

    def _get_tracking_args(self, picking):
        if self.collection.version == '2.0':
            return [{
                "entity": {
                    "order_id": picking.magento_order_id.external_id,
                    "parent_id": picking.external_id,
                    "weight": 0,
                    "qty": 1,
                    "description": picking.name,
                    "track_number": picking.carrier_tracking_ref,
                    "title": picking.carrier_id.magento_tracking_title,
                    "carrier_code": picking.carrier_id.magento_carrier_code,
                }
            }]
        return (picking.carrier_id.magento_carrier_code,
                picking.carrier_id.magento_tracking_title or '',
                picking.carrier_tracking_ref)

    def _validate(self, binding):
        if binding.state != 'done':  # should not happen
            raise ValueError("Wrong value for picking state, "
                             "it must be 'done', found: %s" % binding.state)
        if not binding.carrier_id.magento_carrier_code:
            raise FailedJobError("Wrong value for the Magento carrier code "
                                 "defined in the picking.")

    def _check_allowed_carrier(self, binding, external_id):
        """ Magento2 API does not allow to fetch the list of allowed carriers.
        """
        if self.collection.version == '2.0':
            return
        allowed_carriers = self.backend_adapter.get_carriers(external_id)
        carrier = binding.carrier_id
        if carrier.magento_carrier_code not in allowed_carriers:
            raise FailedJobError("The carrier %(name)s does not accept "
                                 "tracking numbers on Magento.\n\n"
                                 "Tracking codes accepted by Magento:\n"
                                 "%(allowed)s.\n\n"
                                 "Actual tracking code:\n%(code)s\n\n"
                                 "Resolution:\n"
                                 "* Add support of %(code)s in Magento\n"
                                 "* Or deactivate the export of tracking "
                                 "numbers in the setup of the carrier "
                                 "%(name)s." %
                                 {'name': carrier.name,
                                  'allowed': allowed_carriers,
                                  'code': carrier.magento_carrier_code})

    def run(self, binding):
        """ Export the tracking number of a picking to Magento """
        # verify the picking is done + magento id exists
        carrier = binding.carrier_id
        if not carrier:
            return FailedJobError('The carrier is missing on the picking %s.' %
                                  binding.name)

        if not carrier.magento_export_tracking:
            return _('The carrier %s does not export '
                     'tracking numbers.') % carrier.name
        if not binding.carrier_tracking_ref:
            return _('No tracking number to send.')

        sale_binding_id = binding.magento_order_id
        if not sale_binding_id:
            return FailedJobError("No sales order is linked with the picking "
                                  "%s, can't export the tracking number." %
                                  binding.name)

        binder = self.binder_for()
        external_id = binder.to_external(binding)
        if not external_id:
            picking_exporter = self.component(usage='record.exporter')
            picking_exporter.run(binding)
            external_id = binder.to_external(binding)
        if not external_id:
            return FailedJobError("The delivery order %s has no Magento ID, "
                                  "can't export the tracking number." %
                                  binding.name)

        self._validate(binding)
        self._check_allowed_carrier(binding, sale_binding_id.external_id)
        tracking_args = self._get_tracking_args(binding)
        self.backend_adapter.add_tracking_number(external_id, *tracking_args)
