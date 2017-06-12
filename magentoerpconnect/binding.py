# -*- coding: utf-8 -*-
# © 2013-2017 Guewen Baconnier,Camptocamp SA,Akretion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models, fields
from odoo.addons.queue_job.job import job


class MagentoBinding(models.AbstractModel):
    """ Abstract Model for the Bindigs.

    All the models used as bindings between Magento and Odoo
    (``magento.res.partner``, ``magento.product.product``, ...) should
    ``_inherit`` it.
    """
    _name = 'magento.binding'
    _inherit = 'external.binding'
    _description = 'Magento Binding (abstract)'

    # odoo_id = odoo-side id must be declared in concrete model
    backend_id = fields.Many2one(
        comodel_name='magento.backend',
        string='Magento Backend',
        required=True,
        ondelete='restrict',
    )
    # fields.Char because 0 is a valid Magento ID
    # TODO: migration from 'external_id'
    external_id = fields.Char(string='ID on Magento')

    _sql_constraints = [
        ('magento_uniq', 'unique(backend_id, external_id)',
         'A binding already exists with the same Magento ID.'),
    ]

    @job(default_channel='root.magento')
    @api.model
    def import_batch(self, backend, filters=None):
        """ Prepare the import of records modified on Magento """
        if filters is None:
            filters = {}
        work = backend.work_on(self._name)
        importer = work.components(usage='batch.importer')
        return importer.run(filters=filters)
