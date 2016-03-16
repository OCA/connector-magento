# -*- coding: utf-8 -*-
# © 2014 Guewen Baconnier,Damien Crier,Camptocamp SA,Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

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
