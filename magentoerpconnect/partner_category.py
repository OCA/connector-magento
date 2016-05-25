# -*- coding: utf-8 -*-
# © 2013 Guewen Baconnier,Camptocamp SA,Akretion
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import models, fields
from openerp.addons.connector.unit.mapper import (mapping,
                                                  only_create,
                                                  ImportMapper
                                                  )
from .unit.backend_adapter import GenericAdapter
from .unit.import_synchronizer import DelayedBatchImporter
from .backend import magento


class ResPartnerCategory(models.Model):
    _inherit = 'res.partner.category'

    magento_bind_ids = fields.One2many(
        comodel_name='magento.res.partner.category',
        inverse_name='openerp_id',
        string='Magento Bindings',
        readonly=True,
    )


class MagentoResPartnerCategory(models.Model):
    _name = 'magento.res.partner.category'
    _inherit = 'magento.binding'
    _inherits = {'res.partner.category': 'openerp_id'}

    openerp_id = fields.Many2one(comodel_name='res.partner.category',
                                 string='Partner Category',
                                 required=True,
                                 ondelete='cascade')
    # TODO : replace by a m2o when tax class will be implemented
    tax_class_id = fields.Integer(string='Tax Class ID')


@magento
class PartnerCategoryAdapter(GenericAdapter):
    _model_name = 'magento.res.partner.category'
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


@magento
class PartnerCategoryBatchImporter(DelayedBatchImporter):
    """ Delay import of the records """
    _model_name = ['magento.res.partner.category']


PartnerCategoryBatchImport = PartnerCategoryBatchImporter  # deprecated


@magento
class PartnerCategoryImportMapper(ImportMapper):
    _model_name = 'magento.res.partner.category'

    direct = [
        ('customer_group_code', 'name'),
        ('tax_class_id', 'tax_class_id'),
    ]

    @mapping
    def magento_id(self, record):
        return {'magento_id': record['customer_group_id']}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}

    @only_create
    @mapping
    def openerp_id(self, record):
        """ Will bind the category on a existing one with the same name."""
        existing = self.env['res.partner.category'].search(
            [('name', '=', record['customer_group_code'])],
            limit=1,
        )
        if existing:
            return {'openerp_id': existing.id}
