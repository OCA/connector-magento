# Copyright 2013-2019 Camptocamp SA
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import _

from odoo.addons.component.core import Component
from odoo.addons.queue_job.exception import FailedJobError

_logger = logging.getLogger(__name__)


class MagentoTrackingExporter(Component):
    _name = "magento.stock.tracking.exporter"
    _inherit = "magento.exporter"
    _apply_on = ["magento.stock.picking"]
    _usage = "tracking.exporter"

    def _get_tracking_args(self, picking):
        if self.collection.version == "2.0":
            return [
                {
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
                }
            ]
        return (
            picking.carrier_id.magento_carrier_code,
            picking.carrier_id.magento_tracking_title or "",
            picking.carrier_tracking_ref,
        )

    def _validate(self, binding):
        if binding.state != "done":  # should not happen
            raise ValueError(
                "Wrong value for picking state, "
                f"it must be 'done', found: {binding.state}"
            )
        if not binding.carrier_id.magento_carrier_code:
            raise FailedJobError(
                "Wrong value for the Magento carrier code " "defined in the picking."
            )

    def _check_allowed_carrier(self, binding, external_id):
        """Magento2 API does not allow to fetch the list of allowed carriers."""
        if self.collection.version == "2.0":
            return
        allowed_carriers = self.backend_adapter.get_carriers(external_id)
        carrier = binding.carrier_id
        if carrier.magento_carrier_code not in allowed_carriers:
            raise FailedJobError(
                f"The carrier {carrier.name} does not accept "
                "tracking numbers on Magento.\n\n"
                "Tracking codes accepted by Magento:\n"
                f"{allowed_carriers}.\n\n"
                f"Actual tracking code:\n{carrier.magento_carrier_code}\n\n"
                "Resolution:\n"
                f"* Add support of {carrier.magento_carrier_code} in Magento\n"
                "* Or deactivate the export of tracking "
                "numbers in the setup of the carrier "
                f"{carrier.name}."
            )

    def run(self, binding):
        """Export the tracking number of a picking to Magento"""
        # verify the picking is done + magento id exists
        carrier = binding.carrier_id
        if not carrier:
            return FailedJobError(
                f"The carrier is missing on the picking {binding.name}."
            )

        if not carrier.magento_export_tracking:
            return (
                _("The carrier %s does not export " "tracking numbers.") % carrier.name
            )
        if not binding.carrier_tracking_ref:
            return _("No tracking number to send.")

        sale_binding_id = binding.magento_order_id
        if not sale_binding_id:
            return FailedJobError(
                "No sales order is linked with the picking "
                f"{binding.name}, can't export the tracking number."
            )

        binder = self.binder_for()
        external_id = binder.to_external(binding)
        if not external_id:
            picking_exporter = self.component(usage="record.exporter")
            picking_exporter.run(binding)
            external_id = binder.to_external(binding)
        if not external_id:
            return FailedJobError(
                f"The delivery order {binding.name} has no Magento ID, "
                "can't export the tracking number."
            )

        self._validate(binding)
        self._check_allowed_carrier(binding, sale_binding_id.external_id)
        tracking_args = self._get_tracking_args(binding)
        self.backend_adapter.add_tracking_number(external_id, *tracking_args)
