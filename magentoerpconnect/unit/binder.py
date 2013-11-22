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

from datetime import datetime
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.addons.connector.connector import Binder
from ..backend import magento


class MagentoBinder(Binder):
    """ Generic Binder for Magento """


@magento
class MagentoModelBinder(MagentoBinder):
    """
    Bindings are done directly on the binding model.

    Binding models are models called ``magento.{normal_model}``,
    like ``magento.res.partner`` or ``magento.product.product``.
    They are ``_inherits`` of the normal models and contains
    the Magento ID, the ID of the Magento Backend and the additional
    fields belonging to the Magento instance.
    """
    _model_name = [
            'magento.website',
            'magento.store',
            'magento.storeview',
            'magento.res.partner',
            'magento.address',
            'magento.res.partner.category',
            'magento.product.category',
            'magento.product.product',
            'magento.stock.picking.out',
            'magento.sale.order',
            'magento.sale.order.line',
            'magento.account.invoice',
        ]

    def to_openerp(self, external_id, unwrap=False):
        """ Give the OpenERP ID for an external ID

        :param external_id: external ID for which we want the OpenERP ID
        :param unwrap: if True, returns the openerp_id of the magento_xxxx record,
                       else return the id (binding id) of that record
        :return: a record ID, depending on the value of unwrap,
                 or None if the external_id is not mapped
        :rtype: int
        """
        binding_ids = self.session.search(
                self.model._name,
                [('magento_id', '=', str(external_id)),
                 ('backend_id', '=', self.backend_record.id)])
        if not binding_ids:
            return None
        assert len(binding_ids) == 1, "Several records found: %s" % binding_ids
        binding_id = binding_ids[0]
        if unwrap:
            return self.session.read(self.model._name,
                                     binding_id,
                                     ['openerp_id'])['openerp_id'][0]
        else:
            return binding_id

    def to_backend(self, record_id, wrap=False):
        """ Give the external ID for an OpenERP ID

        :param record_id: OpenERP ID for which we want the external id
        :param wrap: if False, record_id is the ID of the binding,
            if True, record_id is the ID of the normal record, the
            method will search the corresponding binding and returns
            the backend id of the binding
        :return: backend identifier of the record
        """
        if wrap:
            erp_id = self.session.search(self.model._name, [
                ['openerp_id', '=', record_id],
                ['backend_id', '=', self.backend_record.id]
            ])
            if erp_id:
                record_id = erp_id[0]
            else:
                return None
        magento_record = self.session.read(self.model._name,
                                           record_id,
                                           ['magento_id'])
        assert magento_record
        return magento_record['magento_id']

    def bind(self, external_id, binding_id):
        """ Create the link between an external ID and an OpenERP ID and
        update the last synchronization date.

        :param external_id: External ID to bind
        :param binding_id: OpenERP ID to bind
        :type binding_id: int
        """
        # avoid to trigger the export when we modify the `magento_id`
        context = self.session.context.copy()
        context['connector_no_export'] = True
        now_fmt = datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        self.environment.model.write(
            self.session.cr,
            self.session.uid,
            binding_id,
            {'magento_id': str(external_id),
             'sync_date': now_fmt},
            context=context)
