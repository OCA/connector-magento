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

from openerp.osv import fields, orm
from openerp.addons.connector.unit.mapper import (mapping,
                                                  only_create,
                                                  ImportMapper
                                                  )
from .unit.backend_adapter import GenericAdapter
from .unit.import_synchronizer import DelayedBatchImport
from .backend import magento


class res_partner_category(orm.Model):
    _inherit = 'res.partner.category'

    _columns = {
        'magento_bind_ids': fields.one2many(
            'magento.res.partner.category',
            'openerp_id',
            string='Magento Bindings',
            readonly=True),
    }

    def copy_data(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default['magento_bind_ids'] = False
        return super(res_partner_category, self).copy_data(cr, uid, id,
                                                           default=default,
                                                           context=context)


class magento_res_partner_category(orm.Model):
    _name = 'magento.res.partner.category'
    _inherit = 'magento.binding'
    _inherits = {'res.partner.category': 'openerp_id'}

    _columns = {
        'openerp_id': fields.many2one('res.partner.category',
                                       string='Partner Category',
                                       required=True,
                                       ondelete='cascade'),
        #TODO : replace by a m2o when tax class will be implemented
        'tax_class_id': fields.integer('Tax Class ID'),
    }

    _sql_constraints = [
        ('magento_uniq', 'unique(backend_id, magento_id)',
         'A partner tag with same ID on Magento already exists.'),
    ]


@magento
class PartnerCategoryAdapter(GenericAdapter):
    _model_name = 'magento.res.partner.category'
    _magento_model = 'ol_customer_groups'

    def search(self, filters=None):
        """ Search records according to some criterias
        and returns a list of ids

        :rtype: list
        """
        return [int(row['customer_group_id']) for row
                in self._call('%s.list' % self._magento_model,
                              [filters] if filters else [{}])]


@magento
class PartnerCategoryBatchImport(DelayedBatchImport):
    """ Delay import of the records """
    _model_name = ['magento.res.partner.category']


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
        sess = self.session
        tag_ids = sess.search('res.partner.category',
                              [('name', '=', record['customer_group_code'])])
        if tag_ids:
            return {'openerp_id': tag_ids[0]}
