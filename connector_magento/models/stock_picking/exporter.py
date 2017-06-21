# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import xmlrpclib

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
            sale_line = line.procurement_id.sale_line_id
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
        if binding.external_id:
            return _('Already exported')
        picking_method = binding.picking_method
        if picking_method == 'complete':
            args = self._get_args(binding)
        elif picking_method == 'partial':
            lines_info = self._get_lines_info(binding)
            if not lines_info:
                raise NothingToDoJob(_('Canceled: the delivery order does not '
                                       'contain lines from the original '
                                       'sale order.'))
            args = self._get_args(binding, lines_info)
        else:
            raise ValueError("Wrong value for picking_method, authorized "
                             "values are 'partial' or 'complete', "
                             "found: %s" % picking_method)
        try:
            external_id = self.backend_adapter.create(*args)
        except xmlrpclib.Fault as err:
            # When the shipping is already created on Magento, it returns:
            # <Fault 102: u"Impossible de faire
            # l\'exp\xe9dition de la commande.">
            if err.faultCode == 102:
                raise NothingToDoJob('Canceled: the delivery order already '
                                     'exists on Magento (fault 102).')
            else:
                raise
        else:
            self.binder.bind(external_id, binding)
            # ensure that we store the external ID
            if not odoo.tools.config['test_enable']:
                self.env.cr.commit()
