# Copyright 2017 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64
import logging
import io
import contextlib
import json

from odoo.exceptions import UserError

from odoo import api, fields, models, tools, _
from odoo.addons.component import core

_logger = logging.getLogger(__name__)


class MagentoBindingBackendRead(models.TransientModel):

    _name = 'magento.binding.backend.read'
    _description = 'Magento Generic Object Reader Wizard'

    @api.model
    @tools.ormcache_context('self._uid', 'model_name', keys=('lang',))
    def _get_translated_model_name(self, model_name):
        # get the translated model name to build
        # a meaningful model description
        search_result = self.env['ir.model'].name_search(
            model_name, operator='=')
        if search_result:
            return search_result[0][1]
        return self.env[model_name]._description

    @api.model
    def _default_magento_backend_id(self):
        active_model = self._context.get('active_model')
        if active_model and active_model == self._name:
            # method called when the result is displayed
            return self.env['magento.backend'].browse([])
        if active_model and active_model != 'magento.backend':
            raise UserError(_("The wizard must be launched from a magento "
                              "backend model"))
        active_id = self._context.get('active_ids', [])
        if len(active_id) > 1:
            raise UserError(_("The wizard must be launched on a single "
                              "magento backend instance"))
        active_id = (active_id and active_id[0]) or self._context.get(
            'active_id')
        return self.env['magento.backend'].browse(active_id)

    @api.model
    def _get_magento_binding_model(self):
        """
        This method return a list of magento bindings for which a backend
        adapter is registered
        :return:
        """
        try:
            components_registry = core._component_databases[self.env.cr.dbname]
        except KeyError:
            _logger.info(
                'No component registry for database %s. '
                'Probably because the Odoo registry has not been built '
                'yet.')
            return []
        component_classes = components_registry.lookup(
            collection_name='magento.backend',
            usage='backend.adapter',
        )
        ret = []
        for component_class in component_classes:
            apply_on = component_class._apply_on
            if not apply_on:
                continue
            if isinstance(apply_on, str):
                apply_on = [apply_on]
            for model_name in apply_on:
                ret.append(
                    (model_name,
                     self._get_translated_model_name(model_name))
                )
        return ret

    name = fields.Char(
        'File Name',
        readonly=True
    )
    data = fields.Binary(
        'File',
        readonly=True
    )
    state = fields.Selection(
        [('choose', 'choose'),
         ('get', 'get')],
        default='choose'
    )
    magento_backend_id = fields.Many2one(
        'magento.backend',
        required=True,
        readonly=True,
        default=_default_magento_backend_id,
    )
    magento_binding_model = fields.Selection(
        '_get_magento_binding_model',
        required=True
    )
    magento_id = fields.Char(
        'Magento Id',
        required=True
    )

    @api.multi
    def action_get_info(self):
        self.ensure_one()

        with self.magento_backend_id.work_on(
                self.magento_binding_model) as work:
            adapter = work.component(usage='backend.adapter')
            data = adapter.read(self.magento_id)
        with contextlib.closing(io.StringIO()) as buf:
            json.dump(data, buf)
            out = base64.encodestring(buf.getvalue())

        name = 'sale_order_%s.json' % self.magento_id
        self.write({'state': 'get', 'data': out, 'name': name})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'magento.binding.backend.read',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }
