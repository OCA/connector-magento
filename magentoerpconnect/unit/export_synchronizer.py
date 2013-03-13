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
import openerp.addons.connector as connector
from ..backend import magento

_logger = logging.getLogger(__name__)



class MagentoExportSynchronizer(connector.ExportSynchronizer):
    """ Base exporter for Magento """

    def __init__(self, environment):
        """
        :param environment: current environment (backend, session, ...)
        :type environment: :py:class:`connector.connector.Environment`
        """
        super(MagentoExportSynchronizer, self).__init__(environment)
        self.openerp_id = None
        self.openerp_record = None

    def _get_openerp_data(self):
        """ Return the raw OpenERP data for ``self.openerp_id`` """
        cr, uid, context = (self.session.cr,
                            self.session.uid,
                            self.session.context)
        return self.model.browse(cr, uid, self.openerp_id, context=context)

    def _has_to_skip(self):
        """ Return True if the import can be skipped """
        return False

    def _export_dependencies(self):
        """ Export the dependencies for the record"""
        return

    def _map_data(self, fields=None):
        """ Return the external record converted to OpenERP """
        return self.mapper.convert(self.openerp_record, fields=fields)

    def _validate_data(self, data):
        """ Check if the values to import are correct

        Pro-actively check before the ``Model.create`` or
        ``Model.update`` if some fields are missing

        Raise `InvalidDataError`
        """
        return

    def _create(self, data):
        """ Create the Magento record """
        magento_id = self.backend_adapter.create(data)
        return magento_id

    def _update(self, magento_id, data):
        """ Update an Magento record """
        self.backend_adapter.write(magento_id, data)

    def run(self, openerp_id, fields=None):
        """ Run the synchronization

        :param openerp_id: identifier of the record
        """
        self.openerp_id = openerp_id
        self.openerp_record = self._get_openerp_data()

        magento_id = self.binder.to_backend(self.openerp_id)
        if not magento_id:
            fields = None  # should be created with all the fields

        if self._has_to_skip():
            return

        # import the missing linked resources
        self._export_dependencies()

        record = self._map_data(fields=fields)
        if not record:
            raise connector.NothingToDoJob

        # special check on data before import
        self._validate_data(record)

        if magento_id:
            # FIXME magento record could have been deleted,
            # we would need to create the record
            # (with all fields)
            self._update(magento_id, record)
        else:
            magento_id = self._create(record)

        self.binder.bind(magento_id, self.openerp_id)
        return _('Record exported with ID %s on Magento.') % magento_id


@magento
class PartnerExport(MagentoExportSynchronizer):
    _model_name = ['magento.res.partner']

@magento
class MagentoPickingSynchronizer(connector.ExportSynchronizer):
    _model_name = ['magento.stock.picking']
    
    def _get_data(self, magento_sale_id, mail_notification=True, lines_info=None):
        if lines_info is None:
            lines_info = {}
        data = [magento_sale_id, lines_info,  _("Shipping Created"), mail_notification, True]
        return data
    
    def _get_lines_info(self, picking):
        """
        @params: picking is an instance of a stock.picking browse record
        
        return : dict of {magento_product_id: quantity}
        """
        so_line_binder = self.get_binder_for_model('magento.sale.order.line')
        item_qty = {}
        # get product and quantities to ship from the picking
        for line in picking.move_lines:
            item_id = so_line_binder.to_backend(line.sale_line_id.id)
            item_qty.setdefault(item_id, 0)
            item_qty[item_id] += line.product_qty
        return item_qty
    
    def _get_picking_mail_option(self, picking):
        """
        @params: picking is an instance of a stock.picking browse record
        
        return : The boolean value of send_picking_done_mail chosen on 
        magento shop
        """
        magento_shop = picking.sale_id.shop_id.magento_bind_ids[0]
        return magento_shop.send_picking_done_mail
        
    def run(self, openerp_id, picking_type):
        """
        Run the job to export the picking with args to ask for partial or complete
        picking.

        @params: picking_type as string, can be 'complete' or 'partial'
        """
        picking_obj = self.pool.get('stock.picking')
        picking = picking_obj.browse(self.session.cr, self.session.uid,
            openerp_id, context=self.session.context)
        sale_id = picking.sale_id.id
        binder = self.get_binder_for_model('magento.sale.order')
        magento_sale_id = binder.to_backend(sale_id)
        mail_notification = self._get_picking_mail_option(picking)
        if picking_type == 'complete':
            data = self._get_data(magento_sale_id, mail_notification)
        elif picking_type == 'partial':
            lines_info = self._get_lines_info(picking)
            data = self._get_data(magento_sale_id, mail_notification, lines_info)
        else:
            raise ValueError("Wrong value for picking_type, authorized value are 'partial' or \
                'complete', found: %s" %picking_type)
        self.backend_adapter.create(data)


@magento
class MagentoTrackingSynchronizer(connector.ExportSynchronizer):
    _model_name = ['magento.stock.picking']
    
    def _get_data(self, magento_picking_id, picking, tracking_number):
        return [magento_picking_id, picking.carrier_id.magento_carrier_code, 
            picking.carrier_id.magento_tracking_title or '', tracking_number]
        
    def run(self, openerp_id, tracking_number):
        """
        Run the job to export the tracking_number to a 'done' picking

        @param: tracking_number of the carrier
        @type: string
        """
        # verify the picking is done + magento id exists
        picking_obj = self.pool.get('stock.picking')
        picking = picking_obj.browse(self.session.cr, self.session.uid,
            openerp_id, context=self.session.context)
        binder = self.get_binder_for_model('magento.stock.picking')
        magento_picking_id = binder.to_backend(picking.id)
        if picking.state != 'done':
            raise ValueError("Wrong value for picking state, it must be 'done', found: %s" %picking.state)
        if not picking.carrier_id:
            raise ValueError("Wrong value for picking carrier_id, you must know the carrier of a picking.")
        if not tracking_number:
            raise ValueError("Wrong value for tracking number, you must provide one.")
        if not picking.carrier_id.magento_carrier_code:
            raise ValueError("Wrong value for the Magento carrier code defined in the picking.")
        if magento_picking_id is None:
            raise connector.NoExternalId("No value found for the picking ID on Magento side, the job will be retry later.")
        data = self._get_data(magento_picking_id, picking, tracking_number)
        self.backend_adapter.add_tracking_number(data)




    
    
    