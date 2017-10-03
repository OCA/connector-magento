# -*- coding: utf-8 -*-
# Copyright 2014-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging

from odoo import api, fields, models
try:
    from odoo.addons.server_environment import serv_config
except ImportError:
    logging.getLogger('odoo.module').warning(
        'server_environment not available in addons path. '
        'server_env_connector_magento will not be usable')

_logger = logging.getLogger(__name__)


class MagentoBackend(models.Model):
    _inherit = 'magento.backend'

    @property
    def _server_env_fields(self):
        return ('location', 'username', 'password')

    @api.multi
    def _compute_server_env(self):
        for backend in self:
            for field_name in self._server_env_fields:
                section_name = '.'.join((self._name.replace('.', '_'),
                                         backend.name))
                try:
                    value = serv_config.get(section_name, field_name)
                    backend[field_name] = value
                except:
                    _logger.exception('error trying to read field %s '
                                      'in section %s', field_name,
                                      section_name)

    location = fields.Char(compute='_compute_server_env')
    username = fields.Char(compute='_compute_server_env')
    password = fields.Char(compute='_compute_server_env')
