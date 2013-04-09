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

import socket
import logging

import magento as magentolib
from openerp.addons.connector.unit.backend_adapter import CRUDAdapter
from openerp.addons.connector.exception import NetworkRetryableError

_logger = logging.getLogger(__name__)


recorder = {}

def call_to_key(method, arguments):
    if isinstance(arguments, list):
        new_args = []
        for arg in arguments:
            if isinstance(arg, dict):
                new_args.append(frozenset(arg))
            elif isinstance(arg, list):
                new_args.append(tuple(arg))
            else:
                new_args.append(arg)
        arguments = new_args
    return (method, tuple(arguments))


def record(method, arguments, result):
    """ Utility function which can be used to record test data
    during synchronisations. Call it from MagentoCRUDAdapter._call

    Then ``output_recorder`` can be used to write the data recorded
    to a file.
    """
    recorder[call_to_key(method, arguments)] = result


def output_recorder(filename):
    import pprint
    with open(filename, 'w') as f:
        pprint.pprint(recorder, f)
    _logger.debug('recorder written to file %s', filename)


class MagentoLocation(object):

    def __init__(self, location, username, password):
        self.location = location
        self.username = username
        self.password = password


class MagentoCRUDAdapter(CRUDAdapter):
    """ External Records Adapter for Magento """

    def __init__(self, environment):
        """

        :param environment: current environment (backend, session, ...)
        :type environment: :py:class:`connector.connector.Environment`
        """
        super(MagentoCRUDAdapter, self).__init__(environment)
        self.magento = MagentoLocation(self.backend_record.location,
                                       self.backend_record.username,
                                       self.backend_record.password)

    def search(self, filters=None):
        """ Search records according to some criterias
        and returns a list of ids """
        raise NotImplementedError

    def read(self, id, attributes=None):
        """ Returns the information of a record """
        raise NotImplementedError

    def search_read(self, filters=None):
        """ Search records according to some criterias
        and returns their information"""
        raise NotImplementedError

    def create(self, data):
        """ Create a record on the external system """
        raise NotImplementedError

    def write(self, id, data):
        """ Update records on the external system """
        raise NotImplementedError

    def delete(self, id):
        """ Delete a record on the external system """
        raise NotImplementedError

    def _call(self, method, arguments):
        try:
            with magentolib.API(self.magento.location,
                                self.magento.username,
                                self.magento.password) as api:
                result = api.call(method, arguments)
                record(method, arguments, result)
                _logger.debug("api.call(%s, %s) returned %s",
                              method, arguments, result)
                return result
        except (socket.gaierror, socket.error, socket.timeout) as err:
            raise NetworkRetryableError(
                'A network error caused the failure of the job: '
                '%s' % err)


class GenericAdapter(MagentoCRUDAdapter):

    _model_name = None
    _magento_model = None

    def search(self, filters=None):
        """ Search records according to some criterias
        and returns a list of ids

        :rtype: list
        """
        return self._call('%s.search' % self._magento_model,
                          [filters] if filters else [{}])

    def read(self, id, attributes=None):
        """ Returns the information of a record

        :rtype: dict
        """
        return self._call('%s.info' % self._magento_model, [id, attributes])

    def search_read(self, filters=None):
        """ Search records according to some criterias
        and returns their information"""
        return self._call('%s.list' % self._magento_model, [filters])

    def create(self, data):
        """ Create a record on the external system """
        return self._call('%s.create' % self._magento_model, [data])

    def write(self, id, data):
        """ Update records on the external system """
        return self._call('%s.update' % self._magento_model, [id, data])

    def delete(self, id):
        """ Delete a record on the external system """
        return self._call('%s.delete' % self._magento_model, [id])
