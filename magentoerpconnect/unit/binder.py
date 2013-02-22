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
from ..backend import magento


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

    def _get_openerp_id(self, magento_identifier):
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
                 ('referential_id', '=', self.backend_record.id)],
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

    def to_openerp(self, magento_identifier):
        """ Give the OpenERP ID for an magento ID

        :param magento_identifier: `ExternalIdentifier` for which
            we want the OpenERP ID
        :return: OpenERP ID of the record
        """
        if magento_identifier:
            expected_oe_id = self._get_openerp_id(magento_identifier)
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

    def to_backend(self, openerp_id):
        """ Give the backend ID for an OpenERP ID

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
                 ('referential_id', '=', self.backend_record.id)],
                context=self.session.context)
        if model_data_ids:
            prefixed_id = data_obj.read(self.session.cr,
                                        self.session.uid,
                                        model_data_ids[0],
                                        ['name'])['name']
            return self._extid_from_prefixed_id(prefixed_id)
        return False

    def bind(self, magento_identifier, openerp_id):
        """ Create the link between an magento ID and an OpenERP ID

        :param magento_identifier: `ExternalIdentifier` to bind
        :param openerp_id: OpenERP ID to bind
        """
        assert isinstance(magento_identifier, connector.RecordIdentifier), (
                "magento_identifier must be an RecordIdentifier")

        _logger.debug('bind openerp_id %s with external_id %s',
                      openerp_id, magento_identifier)

        bind_vals = self._prepare_bind_vals(openerp_id,
                                            magento_identifier)
        return self.session.pool.get('ir.model.data').create(
                self.session.cr, self.session.uid,
                bind_vals, context=self.session.context)

    def _prepare_bind_vals(self, openerp_id, magento_identifier):
        """ Create an external reference for a resource id in the
        ir.model.data table
        """
        module = 'extref/%s' % self.backend_record.name

        bind_vals = {
            'name': self._prefixed_id(magento_identifier),
            'model': self.model._name,
            'res_id': openerp_id,
            'referential_id': self.backend_record.id,
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

    def to_openerp(self, backend_identifier):
        """ Give the OpenERP ID for an external ID

        :param backend_identifier: backend identifiers for which we want
                                   the OpenERP ID
        :type backend_identifier: :py:class:`connector.connector.RecordIdentifier`
        :return: OpenERP ID of the record
        :rtype: int
        """
        openerp_ids = self.environment.model.search(
                self.session.cr,
                self.session.uid,
                [('magento_id', '=', backend_identifier.id),
                 ('backend_id', '=', self.backend_record.id)],
                limit=1,
                context=self.session.context)
        if openerp_ids:
            return openerp_ids[0]

    def to_backend(self, openerp_id):
        """ Give the backend ID for an OpenERP ID

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

    def bind(self, backend_identifier, openerp_id):
        """ Create the link between an external ID and an OpenERP ID

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


@magento
class PartnerBinder(MagentoBinder):
    _model_name = 'res.partner'

    def __init__(self, environment):
        super(PartnerBinder, self).__init__(environment)
        self.model = self.session.pool.get('magento.res.partner')

    def _openerp_website_id(self, magento_website_id):
        binder = connector.Environment(
                self.backend_record,
                self.session,
                'magento.website').env.get_connector_unit(Binder)
        return binder.to_openerp(backend_identifier.website_id)

    def _openerp_bind_id(self, backend_identifier):
        """ Return the ID of the bind model (magento.res.partner)
        or None if the binding does not exist.
        """
        website_id = self._openerp_website_id(backend_identifier.website_id)

        bind_ids = self.model.search(
                self.session.cr,
                self.session.uid,
                [('magento_id', '=', backend_identifier.id),
                 ('website_id', '=', website_id)],
                limit=1,
                context=self.session.context)
        if bind_ids:
            return bind_ids[0]

    def to_openerp(self, backend_identifier):
        """ Give the OpenERP ID for an external ID

        :param backend_identifier: backend identifiers for which we want
                                   the OpenERP ID
        :type backend_identifier: :py:class:`connector.connector.RecordIdentifier`
        :return: OpenERP ID of the record
        :rtype: int
        """
        bind_id = self._openerp_bind_id(backend_identifier)
        if bind_id is not None:
            return self.model.read(self.session.cr,
                                   self.session.uid,
                                   bind_id,
                                   ['partner_id'],
                                   context=self.session.context)['partner_id']
        return None

    # need the website_id
    def to_backend(self, openerp_id):
        raise NotImplementedError

    def bind(self, backend_identifier, openerp_id, metadata=None):
        """ Create the link between an external ID and an OpenERP ID

        :param backend_identifier: Backend identifiers to bind
        :type backend_identifier: :py:class:`connector.connector.RecordIdentifier`
        :param openerp_id: OpenERP ID to bind
        :type openerp_id: int
        :param metadata: optional values to store on the relation model
        :type metadata: dict
        """
        bind_id = self._openerp_bind_id(backend_identifier)
        # TODO all the values could come from the @metadata in the
        # mapping
        website_id = self._openerp_website_id(backend_identifier.website_id)
        bind_vals = {'partner_id': openerp_id,
                     'magento_id': backend_identifier.id,
                     'website_id': website_id}
        if metadata is not None:
            bind_vals.update(metadata)

        if bind_id is None:
            self.model.create(self.session.cr,
                              self.session.uid,
                              bind_vals,
                              context=self.session.context)
        else:
            self.model.write(self.session.cr,
                             self.session.uid,
                             bind_id,
                             bind_vals,
                             context=self.session.context)
