# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2014 Camptocamp SA
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
from openerp import fields, models, api
try:
    from openerp.addons.server_environment import serv_config
except ImportError:
    logging.getLogger('openerp.module').warning(
        'server_environment not available in addons path. '
        'server_env_magentoerpconnect will not be usable')

_logger = logging.getLogger(__name__)


class magento_backend(models.Model):
    _inherit = 'magento.backend'

    location = fields.Char(
        compute='_get_environment_config_by_name',
        readonly=True,
        required=False,
    )
    username = fields.Char(
        compute='_get_environment_config_by_name',
        readonly=True,
        required=False,
        )
    password = fields.Char(
        compute='_get_environment_config_by_name',
        readonly=True,
        required=False,
    )

    @api.model
    def _get_env_fields(self):
        """Return the list of fields that are concerned
        by the environment setup

        :return: a list of field name
        :rtype: list
        """

        return ['password', 'username', 'location']

    @api.multi
    def _get_environment_config_by_name(self):
        """Compute the fields values for current environment"""
        for backend in self:
            for field_name in backend._get_env_fields():
                section_name = '.'.join(
                    (backend._name.replace('.', '_'), backend.name)
                )
                try:
                    value = serv_config.get(section_name, field_name)
                    backend[field_name] = value
                except:
                    _logger.exception('error trying to read field %s '
                                      'in section %s', field_name,
                                      section_name)
                    backend[field_name] = False
