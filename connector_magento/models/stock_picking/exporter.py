# Copyright 2013-2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import xmlrpc.client

import odoo
from odoo import _
from odoo.addons.component.core import Component
from odoo.addons.queue_job.exception import NothingToDoJob


class MagentoPickingExporter(Component):
    _name = 'magento.stock.picking.exporter'
    _inherit = 'magento.exporter'
    _apply_on = ['magento.stock.picking']

    def _get_args(self, binding, lines_info=None):
        if lines_info is None:
            lines_info = {}
        sale_binder = self.binder_for('magento.sale.order')
        magento_sale_id = sale_binder.to_external(binding.magento_order_id)
        mail_notification = self._get_picking_mail_option(binding)
        return (magento_sale_id, lines_info,
                _("Shipping Created"), mail_notification, True)

    def _get_lines_info(self, binding):
        """
        Get the line to export to Magento. In case some lines doesn't have a
        matching on Magento, we ignore them. This allow to add lines manually.

        :param binding: magento.stock.picking record
        :return: dict of {magento_product_id: quantity}
        :rtype: dict
        """
        item_qty = {}
        # get product and quantities to ship from the picking
        for line in binding.move_lines:
            sale_line = line.sale_line_id
            if not sale_line.magento_bind_ids:
                continue
            magento_sale_line = next(
                (line for line in sale_line.magento_bind_ids
                 if line.backend_id.id == binding.backend_id.id),
                None
            )
            if not magento_sale_line:
                continue
            item_id = magento_sale_line.external_id
            item_qty.setdefault(item_id, 0)
            item_qty[item_id] += line.product_qty
        return item_qty

    def _get_picking_mail_option(self, binding):
        """ Indicates if Magento has to send an email

        :param binding: magento.stock.picking record
        :returns: value of send_picking_done_mail chosen on magento shop
        :rtype: boolean
        """
        magento_shop = binding.sale_id.magento_bind_ids[0].store_id
        return magento_shop.send_picking_done_mail

    def run(self, binding):
        """
        Export the picking to Magento
        """
        def get_lines_info():
            lines_info = self._get_lines_info(binding)
            if not lines_info:
                raise NothingToDoJob(
                    _('Canceled: the delivery order does not '
                      'contain lines from the original sale order.'))
            return lines_info

        if binding.external_id:
            return _('Already exported')

        if self.collection.version == '1.7':
            picking_method = binding.picking_method
            if picking_method == 'complete':
                args = self._get_args(binding)
            elif picking_method == 'partial':
                lines_info = get_lines_info()
                args = self._get_args(binding, lines_info)
            else:
                raise ValueError("Wrong value for picking_method, authorized "
                                 "values are 'partial' or 'complete', "
                                 "found: %s" % picking_method)
            try:
                external_id = self.backend_adapter.create(*args)
            except xmlrpc.client.Fault as err:
                # When the shipping is already created on Magento, it returns:
                # <Fault 102: u"Impossible de faire
                # l\'exp\xe9dition de la commande.">
                if err.faultCode == 102:
                    raise NothingToDoJob(
                        'Canceled: the delivery order already '
                        'exists on Magento (fault 102).')
                raise

        else:  # Magento 2.x
            arguments = {
                'items': [{
                    'order_item_id': key,
                    'qty': val,
                } for key, val in get_lines_info().items()]
            }
            external_id = self.backend_adapter._call(
                'order/%s/ship' %
                binding.sale_id.magento_bind_ids[0].external_id,
                arguments, http_method='post')

        self.binder.bind(external_id, binding)
        # ensure that we store the external ID
        if not odoo.tools.config['test_enable']:
            # pylint: disable=invalid-commit
            self.env.cr.commit()  # noqa
