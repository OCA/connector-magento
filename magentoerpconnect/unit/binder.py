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

from openerp.addons.connector.connector import Binder
from ..backend import magento


class MagentoBinder(Binder):
    """ Generic Binder for Magento """


@magento
class MagentoModelBinder(MagentoBinder):
    """
    Bindings are done directly on the model
    """
    _model_name = [
            'magento.website',
            'magento.store',
            'magento.storeview',
            'magento.res.partner',
            'magento.address',
            'magento.res.partner.category',
            'magento.product.category',
            'magento.stock.picking',
            'magento.sale.order',
            'magento.sale.order.line',
        ]

    def to_openerp(self, backend_id):
        """ Give the OpenERP ID for an external ID

        :param backend_id: backend ID for which we want the OpenERP ID
        :return: OpenERP ID of the record
        :rtype: int
        """
        openerp_ids = self.environment.model.search(
                self.session.cr,
                self.session.uid,
                [('magento_id', '=', backend_id),
                 ('backend_id', '=', self.backend_record.id)],
                limit=1,
                context=self.session.context)
        if openerp_ids:
            return openerp_ids[0]

    def to_backend(self, openerp_id):
        """ Give the backend ID for an OpenERP ID

        :param openerp_id: OpenERP ID for which we want the backend id
        :return: backend identifier of the record
        """
        magento_id = self.environment.model.read(
                self.session.cr,
                self.session.uid,
                openerp_id,
                ['magento_id'],
                self.session.context)['magento_id']
        return magento_id

    def bind(self, backend_id, openerp_id):
        """ Create the link between an external ID and an OpenERP ID

        :param backend_id: Backend ID to bind
        :param openerp_id: OpenERP ID to bind
        :type openerp_id: int
        """
        # avoid to trigger the export when we modify the `magento_id`
        context = dict(self.session.context, connector_no_export=True)
        self.environment.model.write(
                self.session.cr,
                self.session.uid,
                openerp_id,
                {'magento_id': backend_id},
                context=context)
