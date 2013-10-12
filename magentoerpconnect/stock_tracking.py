# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2013 Camptocamp SA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import logging
from openerp.tools.translate import _
from openerp.addons.connector.queue.job import job
from openerp.addons.connector.exception import FailedJobError, NoExternalId
from openerp.addons.connector.unit.synchronizer import ExportSynchronizer
from openerp.addons.connector_ecommerce.event import on_tracking_number_added
from .connector import get_environment
from .backend import magento

_logger = logging.getLogger(__name__)


@magento
class MagentoTrackingExport(ExportSynchronizer):
    _model_name = ['magento.stock.picking.out']

    def _get_tracking_args(self, picking):
        return (picking.carrier_id.magento_carrier_code,
                picking.carrier_id.magento_tracking_title or '',
                picking.carrier_tracking_ref)

    def _validate(self, picking):
        if picking.state != 'done':  # should not happen
            raise ValueError("Wrong value for picking state, "
                             "it must be 'done', found: %s" % picking.state)
        if not picking.carrier_id.magento_carrier_code:
            raise FailedJobError("Wrong value for the Magento carrier code "
                                 "defined in the picking.")

    def _check_allowed_carrier(self, picking, magento_id):
        allowed_carriers = self.backend_adapter.get_carriers(magento_id)
        carrier = picking.carrier_id
        if carrier.magento_carrier_code not in allowed_carriers:
            raise FailedJobError("The carrier %(name)s does not accept "
                                 "tracking numbers on Magento.\n\n"
                                 "Tracking codes accepted by Magento:\n"
                                 "%(allowed)s.\n\n"
                                 "Actual tracking code:\n%(code)s\n\n"
                                 "Resolution:\n"
                                 "* Add support of %(code)s in Magento\n"
                                 "* Or deactivate the export of tracking "
                                 "numbers in the setup of the carrier %(name)s." %
                                 {'name': carrier.name,
                                  'allowed': allowed_carriers,
                                  'code': carrier.magento_carrier_code})

    def run(self, binding_id):
        """ Export the tracking number of a picking to Magento """
        # verify the picking is done + magento id exists
        picking = self.session.browse(self.model._name, binding_id)
        carrier = picking.carrier_id
        if not carrier:
            return FailedJobError('The carrier is missing on the picking %s.' %
                                  picking.name)

        if not carrier.magento_export_tracking:
            return _('The carrier %s does not export '
                     'tracking numbers.') % carrier.name
        if not picking.carrier_tracking_ref:
            return _('No tracking number to send.')

        sale_binding_id = picking.magento_order_id
        if not sale_binding_id:
            return FailedJobError("No sales order is linked with the picking "
                                  "%s, can't export the tracking number." %
                                  picking.name)

        magento_picking_id = picking.magento_id
        if magento_picking_id is None:
            raise NoExternalId("No value found for the picking ID on "
                               "Magento side, the job will be retried later.")

        self._validate(picking)
        self._check_allowed_carrier(picking, sale_binding_id.magento_id)
        tracking_args = self._get_tracking_args(picking)
        self.backend_adapter.add_tracking_number(magento_picking_id,
                                                 *tracking_args)


@on_tracking_number_added
def delay_export_tracking_number(session, model_name, record_id):
    """
    Call a job to export the tracking number to a existing picking that
    must be in done state.
    """
    # browse on stock.picking because we cant read on stock.picking.out
    # buggy virtual models... Anyway the ID is the same
    picking = session.browse('stock.picking', record_id)
    for binding in picking.magento_bind_ids:
        # Set the priority to 20 to have more chance that it would be
        # executed after the picking creation
        export_tracking_number.delay(session,
                                     binding._model._name,
                                     binding.id,
                                     priority=20)


@job
def export_tracking_number(session, model_name, record_id):
    """ Export the tracking number of a delivery order. """
    picking = session.browse(model_name, record_id)
    backend_id = picking.backend_id.id
    env = get_environment(session, model_name, backend_id)
    tracking_exporter = env.get_connector_unit(MagentoTrackingExport)
    return tracking_exporter.run(record_id)
