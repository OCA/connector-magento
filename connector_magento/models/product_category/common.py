# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# © 2016 Sodexis
# © 2019 Callino
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import xmlrpc.client
from odoo import models, fields, api
from odoo.addons.connector.exception import IDMissingInBackend
from odoo.addons.component.core import Component
from ...components.backend_adapter import MAGENTO_DATETIME_FORMAT

_logger = logging.getLogger(__name__)


class MagentoProductPosition(models.Model):
    _name = 'magento.product.position'
    _description = 'Magento Product Position'
    _order = 'position asc'
    _rec_name = "name"

    @api.depends('magento_product_category_id', 'product_template_id')
    def _compute_name(self):
        for position in self:
            position.name = "%s in category %s on position %s" % (position.product_template_id.display_name, position.magento_product_category_id.magento_name, position.position)

    name = fields.Char(compute='_compute_name', store=True, string="Name")
    magento_product_category_id = fields.Many2one('magento.product.category', required=True, ondelete='cascade', string='Magento Category')
    product_template_id = fields.Many2one('product.template', required=True, ondelete='cascade', string='Product')
    position = fields.Integer('Position')


class MagentoProductCategory(models.Model):
    _name = 'magento.product.category'
    _inherit = 'magento.binding'
    _description = 'Magento Product Category'
    _magento_backend_path = 'catalog/category/edit/id'
    _magento_frontend_path = 'catalog/category/view/id'
    _rec_name = 'magento_name'

    odoo_id = fields.Many2one(comodel_name='product.category',
                              string='Product Category',
                              required=False,
                              ondelete='cascade')
    magento_name = fields.Char(string='Name')
    description = fields.Text(translate=True)
    magento_parent_id = fields.Many2one(
        comodel_name='magento.product.category',
        string='Magento Parent Category',
        ondelete='cascade',
    )
    magento_child_ids = fields.One2many(
        comodel_name='magento.product.category',
        inverse_name='magento_parent_id',
        string='Magento Child Categories',
    )
    product_position_ids = fields.One2many(
        comodel_name='magento.product.position',
        inverse_name='magento_product_category_id',
        string="Product Positions"
    )

    @api.multi
    def sync_from_magento(self):
        self.ensure_one()
        with self.backend_id.work_on(self._name) as work:
            if self.backend_id.product_synchro_strategy == 'odoo_first':
                self.sync_to_magento()
            else:
                importer = work.component(usage='record.importer')
                return importer.run(self.external_id, force=True)

    @api.multi
    def update_products(self):
        for mcategory in self:
            # Get tmpl_ids from magento.product.template
            mtemplates = self.env['magento.product.template'].search([
                ('categ_id', '=', mcategory.odoo_id.id),
                ('backend_id', '=', mcategory.backend_id.id),
            ])
            mbundles = self.env['magento.product.bundle'].search([
                ('categ_id', '=', mcategory.odoo_id.id),
                ('backend_id', '=', mcategory.backend_id.id),
            ])
            mproducts = self.env['magento.product.product'].search([
                ('categ_id', '=', mcategory.odoo_id.id),
                ('magento_configurable_id', '=', False),
                ('backend_id', '=', mcategory.backend_id.id),
            ])
            tmpl_ids = [mtemplate.odoo_id.id for mtemplate in mtemplates]
            tmpl_ids.extend(mbundle.odoo_id.id for mbundle in mbundles if mbundle.odoo_id.id not in tmpl_ids)
            tmpl_ids.extend(mproduct.odoo_id.product_tmpl_id.id for mproduct in mproducts if mproduct.odoo_id.product_tmpl_id.id not in tmpl_ids)
            _logger.info("This product template ids are in this category: %s", tmpl_ids)
            # Get list of ids already with position entry
            pt_ids = {}
            for pp in mcategory.product_position_ids:
                pt_ids[pp.product_template_id] = pp.id
            p_tmpl_ids = list(pt_ids.keys())
            ppids = []
            missing = list(set(tmpl_ids) - set(p_tmpl_ids))
            # Create missing entries
            for tmpl_id in missing:
                ppids.append((0, 0, {
                    'product_template_id': tmpl_id,
                    'magento_product_category_id': mcategory.id,
                    'position': 9999,
                }))
            # Remove entries lost
            delete = list(set(p_tmpl_ids) - set(tmpl_ids))
            for tmpl_id in delete:
                ppids.append((3, pt_ids[tmpl_id]))
            mcategory.product_position_ids = ppids



class ProductCategory(models.Model):
    _inherit = 'product.category'

    magento_bind_ids = fields.One2many(
        comodel_name='magento.product.category',
        inverse_name='odoo_id',
        string="Magento Bindings",
    )


class ProductCategoryAdapter(Component):
    _name = 'magento.product.category.adapter'
    _inherit = 'magento.adapter'
    _apply_on = 'magento.product.category'

    _magento_model = 'catalog_category'
    _magento2_model = 'categories'
    _magento2_key = 'id'
    _admin_path = '/{model}/index/'

    def _call(self, method, arguments, http_method=None, storeview=None):
        try:
            return super(ProductCategoryAdapter, self)._call(method, arguments, http_method=http_method, storeview=storeview)
        except xmlrpc.client.Fault as err:
            # 101 is the error in the Magento API
            # when the category does not exist
            if err.faultCode == 102:
                raise IDMissingInBackend
            else:
                raise

    def search(self, filters=None, from_date=None, to_date=None):
        """ Search records according to some criteria and return a
        list of ids

        :rtype: list
        """
        if filters is None:
            filters = {}

        dt_fmt = MAGENTO_DATETIME_FORMAT
        if from_date is not None:
            filters.setdefault('updated_at', {})
            # updated_at include the created records
            filters['updated_at']['from'] = from_date.strftime(dt_fmt)
        if to_date is not None:
            filters.setdefault('updated_at', {})
            filters['updated_at']['to'] = to_date.strftime(dt_fmt)
        
        if self.work.magento_api._location.version == '2.0':
            return super(ProductCategoryAdapter, self).search(filters=filters)
       
        return self._call('oerp_catalog_category.search',
                          [filters] if filters else [{}])

    def read(self, id, storeview_code=None, attributes=None, binding=None):
        """ Returns the information of a record

        :rtype: dict
        """
        if self.work.magento_api._location.version == '2.0':
            # TODO: storeview context in mag 2.0
            return super(ProductCategoryAdapter, self).read(id, attributes)
        return self._call('%s.info' % self._magento_model,
                          [int(id), storeview_code, attributes])

    def tree(self, parent_id=None, storeview_id=None):
        """ Returns a tree of product categories

        :rtype: dict
        """
        if self.work.magento_api._location.version == '2.0':
            raise NotImplementedError  # TODO
        
        def filter_ids(tree):
            children = {}
            if tree['children']:
                for node in tree['children']:
                    children.update(filter_ids(node))
            category_id = {tree['category_id']: children}
            return category_id
        if parent_id:
            parent_id = int(parent_id)
        tree = self._call('%s.tree' % self._magento_model,
                          [parent_id, storeview_id])
        return filter_ids(tree)

    def move(self, categ_id, parent_id, after_categ_id=None):
        if self.work.magento_api._location.version == '2.0':
            return self._call(
                '%s/%s/move' % (self._magento2_model, categ_id), {
                    'parent_id': parent_id,
                    'after_id': after_categ_id,
                })
        return self._call('%s.move' % self._magento_model,
                          [categ_id, parent_id, after_categ_id])

    def get_assigned_product(self, categ_id):
        if self.work.magento_api._location.version == '2.0':
            raise NotImplementedError  # TODO
        return self._call('%s.assignedProducts' % self._magento_model,
                          [categ_id])

    def assign_product(self, categ_id, product_id, position=0):
        if self.work.magento_api._location.version == '2.0':
            raise NotImplementedError  # TODO
        return self._call('%s.assignProduct' % self._magento_model,
                          [categ_id, product_id, position, 'id'])

    def update_product(self, categ_id, product_id, position=0):
        if self.work.magento_api._location.version == '2.0':
            raise NotImplementedError  # TODO
        return self._call('%s.updateProduct' % self._magento_model,
                          [categ_id, product_id, position, 'id'])

    def remove_product(self, categ_id, product_id):
        if self.work.magento_api._location.version == '2.0':
            raise NotImplementedError  # TODO
        return self._call('%s.removeProduct' % self._magento_model,
                          [categ_id, product_id, 'id'])
