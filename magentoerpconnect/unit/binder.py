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

import openerp.addons.connector as connector
from ..reference import magento


class MagentoBinder(connector.Binder):
    """ Generic Binder for Magento """


class IrModelDataBinder(MagentoBinder):
    """ Legacy binding in ir.model.data """

    def _prefixed_id(self, magento_identifier):
        """Return the prefixed_id for an id given
        :param str or int id: magento id
        :rtype str
        :return the prefixed id
        """
        # The reason why we don't just use the magento id and put the
        # model as the prefix is to avoid unique ir_model_data.name per
        # module constraint violation.
        return "%s/%s" % (self.model._name.replace('.', '_'),
                          str(magento_identifier.id))

    def _extid_from_prefixed_id(self, prefixed_id):
        """Return the magento id extracted from an prefixed_id

        :param str prefixed_id: prefixed_id to process
        :rtype int/str
        :return the id extracted
        """
        parsed = prefixed_id.split(self.model._name.replace('.', '_') + '/')[1]

        if parsed.isdigit():
            parsed = int(parsed)
        ext_id = ExternalIdentifier()  # TODO find a good way to manage
                                       # the ExternalIdentifier
        ext_id.id = parsed
        return ext_id

    def _get_openerp_id(self, backend, magento_identifier):
        """Returns the id of the entry in ir.model.data and the expected
        id of the resource in the current model Warning the
        expected_oe_id may not exists in the model, that's the res_id
        registered in ir.model.data
        """
        model_data_obj = self.session.pool.get('ir.model.data')
        model_data_ids = model_data_obj.search(
                self.session.cr,
                self.session.uid,
                [('name', '=', self._prefixed_id(magento_identifier)),
                 ('model', '=', self.model._name),
                 ('referential_id', '=', backend.id)],
                context=self.session.context)
        model_data_id = model_data_ids and model_data_ids[0] or False
        expected_oe_id = False
        if model_data_id:
            expected_oe_id = model_data_obj.read(
                    self.session.cr,
                    self.session.uid,
                    model_data_id,
                    ['res_id'])['res_id']
        return expected_oe_id

    def to_openerp(self, backend, magento_identifier):
        """ Give the OpenERP ID for an magento ID

        :param backend: browse of the external backend
        :param magento_identifier: `ExternalIdentifier` for which
            we want the OpenERP ID
        :return: OpenERP ID of the record
        """
        if magento_identifier:
            expected_oe_id = self._get_openerp_id(
                    backend, magento_identifier)
            # OpenERP cleans up the references in ir.model.data to deleted
            # records only on server updates to avoid performance
            # penalty. Thus, we check if the record really still exists.
            if expected_oe_id:
                if self.model.exists(self.session.cr,
                                     self.session.uid,
                                     expected_oe_id,
                                     context=self.session.context):
                    return expected_oe_id
        return False

    def to_backend(self, backend, openerp_id):
        """ Give the backend ID for an OpenERP ID

        :param backend: browse of the external backend
        :param openerp_id: OpenERP ID for which we want the backend id
        :return: backend identifier of the record
        :rtype: :py:class:`connector.connector.ExternalIdentifier`
        """
        data_obj = self.session.pool.get('ir.model.data')
        model_data_ids = data_obj.search(
                self.session.cr,
                self.session.uid,
                [('model', '=', self.model._name),
                 ('res_id', '=', openerp_id),
                 ('referential_id', '=', backend.id)],
                context=self.session.context)
        if model_data_ids:
            prefixed_id = data_obj.read(self.session.cr,
                                        self.session.uid,
                                        model_data_ids[0],
                                        ['name'])['name']
            return self._extid_from_prefixed_id(prefixed_id)
        return False

    def bind(self, backend, magento_identifier, openerp_id):
        """ Create the link between an magento ID and an OpenERP ID

        :param backend: browse of the external backend
        :param magento_identifier: `ExternalIdentifier` to bind
        :param openerp_id: OpenERP ID to bind
        """
        assert isinstance(magento_identifier, connector.RecordIdentifier), (
                "magento_identifier must be an RecordIdentifier")

        _logger.debug('bind openerp_id %s with external_id %s',
                      openerp_id, magento_identifier)

        bind_vals = self._prepare_bind_vals(backend,
                                            openerp_id,
                                            magento_identifier)
        return self.session.pool.get('ir.model.data').create(
                self.session.cr, self.session.uid,
                bind_vals, context=self.session.context)

    def _prepare_bind_vals(self, backend, openerp_id, magento_identifier):
        """ Create an external reference for a resource id in the
        ir.model.data table
        """
        module = 'extref/%s' % backend.name

        bind_vals = {
            'name': self._prefixed_id(magento_identifier),
            'model': self.model._name,
            'res_id': openerp_id,
            'referential_id': backend.id,
            'module': module
            }
        return bind_vals


@magento
class InModelBinder(MagentoBinder):
    """
    Bindings are done directly on the model
    """
    _model_name = [
            'magento.website',
            'magento.store',
            'magento.storeview',
        ]

    def to_openerp(self, backend, backend_identifier):
        """ Give the OpenERP ID for an external ID

        :param backend: external backend
        :param backend_identifier: backend identifiers for which we want
                                   the OpenERP ID
        :type backend_identifier: :py:class:`connector.connector.RecordIdentifier`
        :return: OpenERP ID of the record
        :rtype: int
        """
        website_ids = self.environment.model.search(
                self.session.cr,
                self.session.uid,
                [('magento_id', '=', backend_identifier.id),
                 ('backend_id', '=', backend.id)],
                limit=1,
                context=self.session.context)
        if website_ids:
            return website_ids[0]

    def to_backend(self, backend, openerp_id):
        """ Give the backend ID for an OpenERP ID

        :param backend: browse of the external backend
        :param openerp_id: OpenERP ID for which we want the backend id
        :return: backend identifier of the record
        :rtype: :py:class:`connector.connector.RecordIdentifier`
        """
        magento_id = self.environment.model.read(
                self.session.cr,
                self.session.uid,
                openerp_id,
                ['magento_id'],
                self.session.context)['magento_id']
        return magento_id

    def bind(self, backend, backend_identifier, openerp_id):
        """ Create the link between an external ID and an OpenERP ID

        :param backend: browse of the external backend
        :param backend_identifier: Backend identifiers to bind
        :type backend_identifier: :py:class:`connector.connector.RecordIdentifier`
        :param openerp_id: OpenERP ID to bind
        :type openerp_id: int
        """
        self.environment.model.write(
                self.session.cr,
                self.session.uid,
                openerp_id,
                {'magento_id': backend_identifier.id},
                self.session.context)
