# -*- coding: utf-8 -*-
# © 2013-2017 Guewen Baconnier,Camptocamp SA,Akretion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models, fields
from odoo.addons.queue_job.job import job, related_action
from urlparse import urljoin


class MagentoBinding(models.AbstractModel):
    """ Abstract Model for the Bindings.

    All the models used as bindings between Magento and Odoo
    (``magento.res.partner``, ``magento.product.product``, ...) should
    ``_inherit`` it.
    """
    _name = 'magento.binding'
    _inherit = 'external.binding'
    _description = 'Magento Binding (abstract)'
    _magento_backend_path = None
    _magento_frontend_path = None

    @api.depends('backend_id', 'external_id')
    def _compute_magento_backend_url(self):
        for binding in self:
            if binding._magento_backend_path:
                binding.magento_backend_url = "%s/%s" % (urljoin(binding.backend_id.admin_location, binding._magento_backend_path), binding.external_id)
            if binding._magento_frontend_path:
                binding.magento_frontend_url = "%s/%s" % (urljoin(binding.backend_id.location, binding._magento_frontend_path), binding.external_id)

    # odoo_id = odoo-side id must be declared in concrete model
    backend_id = fields.Many2one(
        comodel_name='magento.backend',
        string='Magento Backend',
        required=True,
        ondelete='restrict',
    )
    # fields.Char because 0 is a valid Magento ID
    external_id = fields.Char(string='ID on Magento')
    magento_backend_url = fields.Char(string="Magento Backend URL", compute='_compute_magento_backend_url')
    magento_frontend_url = fields.Char(string="Magento Frontend URL", compute='_compute_magento_backend_url')

    #TODO: Setting the constraint here have starange side effects on product_attribute
    _sql_constraints = [
        ('magento_uniq', 'unique(backend_id, external_id)',
         'A binding already exists with the same Magento ID.'),
    ]

    def open_magento_backend(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": self.magento_backend_url,
            "target": "magento_backend",
        }

    def open_magento_frontend(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": self.magento_frontend_url,
            "target": "magento_frontend",
        }

    @job(default_channel='root.magento')
    @api.model
    def import_batch(self, backend, filters=None):
        """ Prepare the import of records modified on Magento """
        if filters is None:
            filters = {}
        with backend.work_on(self._name) as work:
            importer = work.component(usage='batch.importer')
            return importer.run(filters=filters)

    @job(default_channel='root.magento')
    @related_action(action='related_action_magento_link')
    @api.model
    def import_record(self, backend, external_id, force=False):
        """ Import a Magento record """
        with backend.work_on(self._name) as work:
            importer = work.component(usage='record.importer')
            return importer.run(external_id, force=force)

    @job(default_channel='root.magento')
    @related_action(action='related_action_unwrap_binding')
    @api.multi
    def export_record(self, backend_id, fields=None):
        """ Export a record on Magento """
        self.ensure_one()
        with self.backend_id.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            lang = self.backend_id.default_lang_id
            if lang.code != self.env.context.get('lang'):
                self = self.with_context(lang=lang.code)
            return exporter.run(self, fields)

    @job(default_channel='root.magento')
    @related_action(action='related_action_magento_link')
    def export_delete_record(self, backend, external_id):
        """ Delete a record on Magento """
        with backend.work_on(self._name) as work:
            deleter = work.component(usage='record.exporter.deleter')
            return deleter.run(external_id)
