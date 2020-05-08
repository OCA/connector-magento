# © 2013 Guewen Baconnier,Camptocamp SA,Akretion
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields
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
    _magento2_model = 'customerGroups'
    _magento2_search = 'customerGroups/search'
    _magento2_key = 'id'
    _admin_path = '/customer_group/edit/id/{id}'
    # Not valid without security key
    # _admin2_path = '/customer/group/edit/id/{id}'

    def search(self, filters=None):
        """ Search records according to some criterias
        and returns a list of ids

        :rtype: list
        """
        if self.collection.version == '1.7':
            return [int(row['customer_group_id']) for row
                    in self._call('%s.list' % self._magento_model,
                                  [filters] if filters else [{}])]
        return super(PartnerCategoryAdapter, self).search(filters=filters)
