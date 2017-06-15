# -*- coding: utf-8 -*-
# © 2013 Guewen Baconnier,Camptocamp SA,Akretion
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import xmlrpclib
from odoo import models, fields
from odoo.addons.connector.components.mapper import mapping
from odoo.addons.connector.exception import (IDMissingInBackend,
                                             MappingError,
                                             )
from odoo.addons.component.core import Component
from .components.backend_adapter import MAGENTO_DATETIME_FORMAT

_logger = logging.getLogger(__name__)


class MagentoProductCategory(models.Model):
    _name = 'magento.product.category'
    _inherit = 'magento.binding'
    _inherits = {'product.category': 'odoo_id'}
    _description = 'Magento Product Category'

    odoo_id = fields.Many2one(comodel_name='product.category',
                              string='Product Category',
                              required=True,
                              ondelete='cascade')
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
    _admin_path = '/{model}/index/'

    def _call(self, method, arguments):
        try:
            return super(ProductCategoryAdapter, self)._call(method, arguments)
        except xmlrpclib.Fault as err:
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

        return self._call('oerp_catalog_category.search',
                          [filters] if filters else [{}])

    def read(self, id, storeview_id=None, attributes=None):
        """ Returns the information of a record

        :rtype: dict
        """
        return self._call('%s.info' % self._magento_model,
                          [int(id), storeview_id, attributes])

    def tree(self, parent_id=None, storeview_id=None):
        """ Returns a tree of product categories

        :rtype: dict
        """
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
        return self._call('%s.move' % self._magento_model,
                          [categ_id, parent_id, after_categ_id])

    def get_assigned_product(self, categ_id):
        return self._call('%s.assignedProducts' % self._magento_model,
                          [categ_id])

    def assign_product(self, categ_id, product_id, position=0):
        return self._call('%s.assignProduct' % self._magento_model,
                          [categ_id, product_id, position, 'id'])

    def update_product(self, categ_id, product_id, position=0):
        return self._call('%s.updateProduct' % self._magento_model,
                          [categ_id, product_id, position, 'id'])

    def remove_product(self, categ_id, product_id):
        return self._call('%s.removeProduct' % self._magento_model,
                          [categ_id, product_id, 'id'])


class ProductCategoryBatchImporter(Component):
    """ Import the Magento Product Categories.

    For every product category in the list, a delayed job is created.
    A priority is set on the jobs according to their level to rise the
    chance to have the top level categories imported first.
    """
    _name = 'magento.product.category.batch.importer'
    _inherit = 'magento.delayed.batch.importer'
    _apply_on = ['magento.product.category']

    def _import_record(self, external_id, job_options=None):
        """ Delay a job for the import """
        super(ProductCategoryBatchImporter, self)._import_record(
                external_id, job_options=job_options)

    def run(self, filters=None):
        """ Run the synchronization """
        from_date = filters.pop('from_date', None)
        to_date = filters.pop('to_date', None)
        if from_date or to_date:
            updated_ids = self.backend_adapter.search(filters,
                                                      from_date=from_date,
                                                      to_date=to_date)
        else:
            updated_ids = None

        base_priority = 10

        def import_nodes(tree, level=0):
            for node_id, children in tree.iteritems():
                # By changing the priority, the top level category has
                # more chance to be imported before the childrens.
                # However, importers have to ensure that their parent is
                # there and import it if it doesn't exist
                if updated_ids is None or node_id in updated_ids:
                    job_options = {
                        'priority': base_priority + level,
                    }
                    self._import_record(
                        node_id, job_options=job_options)
                import_nodes(children, level=level + 1)
        tree = self.backend_adapter.tree()
        import_nodes(tree)


class ProductCategoryImporter(Component):
    _name = 'magento.product.category.importer'
    _inherit = 'magento.importer'
    _apply_on = ['magento.product.category']

    def _import_dependencies(self):
        """ Import the dependencies for the record"""
        record = self.magento_record
        # import parent category
        # the root category has a 0 parent_id
        self._import_dependency(record.get('parent_id'), self.model)

    def _create(self, data):
        binding = super(ProductCategoryImporter, self)._create(data)
        self.backend_record.add_checkpoint(binding)
        return binding

    def _after_import(self, binding):
        """ Hook called at the end of the import """
        translation_importer = self.component(usage='translation.importer')
        translation_importer.run(self.external_id, binding)


class ProductCategoryImportMapper(Component):
    _name = 'magento.product.category.import.mapper'
    _inherit = 'magento.import.mapper'
    _apply_on = 'magento.product.category'

    direct = [
        ('description', 'description'),
    ]

    @mapping
    def name(self, record):
        if record['level'] == '0':  # top level category; has no name
            return {'name': self.backend_record.name}
        if record['name']:  # may be empty in storeviews
            return {'name': record['name']}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}

    @mapping
    def parent_id(self, record):
        if not record.get('parent_id'):
            return
        binder = self.binder_for()
        parent_binding = binder.to_internal(record['parent_id'])

        if not parent_binding:
            raise MappingError("The product category with "
                               "magento id %s is not imported." %
                               record['parent_id'])

        parent = parent_binding.odoo_id
        return {'parent_id': parent.id, 'magento_parent_id': parent_binding.id}
