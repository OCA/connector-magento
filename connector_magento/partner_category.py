# -*- coding: utf-8 -*-
# © 2013 Guewen Baconnier,Camptocamp SA,Akretion
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields
from odoo.addons.connector.components.mapper import (
    mapping,
    only_create,
)
from odoo.addons.component.core import Component


class ResPartnerCategory(models.Model):
    _inherit = 'res.partner.category'

    magento_bind_ids = fields.One2many(
        comodel_name='magento.res.partner.category',
        inverse_name='odoo_id',
        string='Magento Bindings',
        readonly=True,
    )


class MagentoResPartnerCategory(models.Model):
    _name = 'magento.res.partner.category'
    _inherit = 'magento.binding'
    _inherits = {'res.partner.category': 'odoo_id'}

    odoo_id = fields.Many2one(comodel_name='res.partner.category',
                              string='Partner Category',
                              required=True,
                              ondelete='cascade')
    # TODO : replace by a m2o when tax class will be implemented
    tax_class_id = fields.Integer(string='Tax Class ID')


class PartnerCategoryAdapter(Component):

    _name = 'magento.partner.category.adapter'
    _inherit = 'magento.adapter'
    _apply_on = 'magento.res.partner.category'

    _magento_model = 'ol_customer_groups'
    _admin_path = '/customer_group/edit/id/{id}'

    def search(self, filters=None):
        """ Search records according to some criterias
        and returns a list of ids

        :rtype: list
        """
        return [int(row['customer_group_id']) for row
                in self._call('%s.list' % self._magento_model,
                              [filters] if filters else [{}])]


class PartnerCategoryBatchImporter(Component):
    """ Delay import of the records """
    _name = 'magento.partner.category.batch.importer'
    _inherit = 'magento.delayed.batch.importer'
    _apply_on = 'magento.res.partner.category'


class PartnerCategoryImportMapper(Component):
    _name = 'magento.partner.category.import.mapper'
    _inherit = 'magento.import.mapper'
    _apply_on = 'magento.res.partner.category'

    direct = [
        ('customer_group_code', 'name'),
        ('tax_class_id', 'tax_class_id'),
    ]

    @mapping
    def external_id(self, record):
        return {'external_id': record['customer_group_id']}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}

    @only_create
    @mapping
    def odoo_id(self, record):
        """ Will bind the category on a existing one with the same name."""
        existing = self.env['res.partner.category'].search(
            [('name', '=', record['customer_group_code'])],
            limit=1,
        )
        if existing:
            return {'odoo_id': existing.id}
