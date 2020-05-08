# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import _
from odoo.addons.component.core import Component


class StateExporter(Component):
    _name = 'magento.sale.state.exporter'
    _inherit = 'base.exporter'
    _usage = 'sale.state.exporter'
    _apply_on = 'magento.sale.order'

    ORDER_STATUS_MAPPING = {  # used in connector_magento_order_comment
        'draft': 'pending',
        'manual': 'processing',
        'progress': 'processing',
        'shipping_except': 'processing',
        'invoice_except': 'processing',
        'done': 'complete',
        'cancel': 'canceled',
        'waiting_date': 'holded'
    }

    def run(self, binding, allowed_states=None, comment=None, notify=False):
        """ Change the status of the sales order on Magento.

        It adds a comment on Magento with a status.
        Sales orders on Magento have a state and a status.
        The state is related to the sale workflow, and the status can be
        modified liberaly.  We change only the status because Magento
        handle the state itself.

        When a sales order is modified, if we used the ``sales_order.cancel``
        API method, we would not be able to revert the cancellation.  When
        we send ``cancel`` as a status change with a new comment, we are still
        able to change the status again and to create shipments and invoices
        because the state is still ``new`` or ``processing``.

        :param binding: the binding record of the sales order
        :param allowed_states: list of Odoo states that are allowed
                               for export. If empty, it will export any
                               state.
        :param comment: Comment to display on Magento for the state change
        :param notify: When True, Magento will send an email with the
                       comment
        """
        state = binding.state
        if allowed_states and state not in allowed_states:
            return _('State %s is not exported.') % state
        external_id = self.binder.to_external(binding)
        if not external_id:
            return _('Sale is not linked with a Magento sales order')
        magento_state = self.ORDER_STATUS_MAPPING[state]
        record = self.backend_adapter.read(external_id)
        # Magento2: sometimes only 'state' is present
        if (record.get('status') or record['state']) == magento_state:
            return _('Magento sales order is already '
                     'in state %s') % magento_state
        if self.collection.version == '2.0':
            self.backend_adapter._call(
                'orders',
                {
                    "entity": {
                        "entity_id": external_id,
                        "state": magento_state,
                        "status": magento_state,
                    },
                },
                http_method='post')
            to_notify = comment and notify
            self.backend_adapter._call(
                'orders/%s/comments' % external_id,
                {
                    "statusHistory": {
                        "comment": comment or magento_state,
                        "is_customer_notified": 1 if to_notify else 0,
                        "is_visible_on_front": 0,
                    }
                },
                http_method='post')
        else:
            self.backend_adapter.add_comment(external_id, magento_state,
                                             comment=comment,
                                             notify=notify)
