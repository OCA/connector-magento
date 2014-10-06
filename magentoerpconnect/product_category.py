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

import logging
import xmlrpclib
from openerp.osv import orm, fields
from openerp.addons.connector.unit.mapper import (mapping,
                                                  ImportMapper
                                                  )
from openerp.addons.connector.exception import (IDMissingInBackend,
                                                MappingError,
                                                )
from .unit.backend_adapter import (GenericAdapter,
                                   MAGENTO_DATETIME_FORMAT,
                                   )
from .unit.import_synchronizer import (DelayedBatchImport,
                                       MagentoImportSynchronizer,
                                       TranslationImporter,
                                       AddCheckpoint,
                                       )
from .backend import magento

_logger = logging.getLogger(__name__)


class magento_product_category(orm.Model):
    _name = 'magento.product.category'
    _inherit = 'magento.binding'
    _inherits = {'product.category': 'openerp_id'}
    _description = 'Magento Product Category'

    _columns = {
        'openerp_id': fields.many2one('product.category',
                                      string='Product Category',
                                      required=True,
                                      ondelete='cascade'),
        'description': fields.text('Description', translate=True),
        'is_active': fields.boolean('Active in magento'),
        'include_in_menu': fields.boolean('Include in magento menu'),
        'magento_parent_id': fields.many2one(
            'magento.product.category',
            string='Magento Parent Category',
            ondelete='cascade'),
        'magento_child_ids': fields.one2many(
            'magento.product.category',
            'magento_parent_id',
            string='Magento Child Categories'),
    }

    _defaults = {
        'is_active': True,
        'include_in_menu': False,
    }

    _sql_constraints = [
        ('magento_uniq', 'unique(backend_id, magento_id)',
         'A product category with same ID on Magento already exists.'),
    ]


class product_category(orm.Model):
    _inherit = 'product.category'

    _columns = {
        'magento_bind_ids': fields.one2many(
            'magento.product.category', 'openerp_id',
            string="Magento Bindings"),
    }

    def copy_data(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default['magento_bind_ids'] = False
        return super(product_category, self).copy_data(cr, uid, id,
                                                       default=default,
                                                       context=context)

@magento
class ProductCategoryImageAdapter(GenericAdapter):
    _model_name = 'magento.product.category'
    _magento_model = 'ol_catalog_category_media'

    def create(self, name, binary):
        img = self._call('%s.create' % self._magento_model, [name, binary])
        if img == 'Error in file creation':
            #TODO improve error management
            raise Exception("Image creation: ",
                "Magento tried to insert image (%s) but there is "
                "no sufficient grants in the folder "
                "'media/catalog/category' if it exists" % name)

@magento
class ProductCategoryAdapter(GenericAdapter):
    _model_name = 'magento.product.category'
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

    def create(self, data):
        return self._call('%s.create'% self._magento_model,
                          [data['parent_id'],data])

    def write(self, id, data, storeview=None):
        """ Update records on the external system """
        return self._call('%s.update' % self._magento_model,
                          [int(id), data, storeview])

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


@magento
class ProductCategoryBatchImport(DelayedBatchImport):
    """ Import the Magento Product Categories.

    For every product category in the list, a delayed job is created.
    A priority is set on the jobs according to their level to rise the
    chance to have the top level categories imported first.
    """
    _model_name = ['magento.product.category']

    def _import_record(self, magento_id, priority=None):
        """ Delay a job for the import """
        super(ProductCategoryBatchImport, self)._import_record(
            magento_id, priority=priority)

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
                    self._import_record(node_id, priority=base_priority+level)
                import_nodes(children, level=level+1)
        tree = self.backend_adapter.tree()
        import_nodes(tree)


@magento
class ProductCategoryImport(MagentoImportSynchronizer):
    _model_name = ['magento.product.category']

    def _import_dependencies(self):
        """ Import the dependencies for the record"""
        record = self.magento_record
        env = self.environment
        # import parent category
        # the root category has a 0 parent_id
        if record.get('parent_id'):
            binder = self.get_binder_for_model()
            parent_id = record['parent_id']
            if binder.to_openerp(parent_id) is None:
                importer = env.get_connector_unit(MagentoImportSynchronizer)
                importer.run(parent_id)

    def _create(self, data):
        openerp_binding_id = super(ProductCategoryImport, self)._create(data)
        checkpoint = self.get_connector_unit_for_model(AddCheckpoint)
        checkpoint.run(openerp_binding_id)
        return openerp_binding_id

    def _after_import(self, binding_id):
        """ Hook called at the end of the import """
        translation_importer = self.get_connector_unit_for_model(
            TranslationImporter, self.model._name)
        translation_importer.run(self.magento_id, binding_id)


@magento
class ProductCategoryImportMapper(ImportMapper):
    _model_name = 'magento.product.category'

    direct = [
        ('description', 'description'),
        ('is_active','is_active'),
        ('include_in_menu','include_in_menu')
    ]


    @mapping
    def name(self, record):
        if record['level'] == '0':  # top level category; has no name
            return {'name': self.backend_record.name}
        if record['name']:  # may be empty in storeviews
            return {'name': record['name']}

    @mapping
    def magento_id(self, record):
        return {'magento_id': record['category_id']}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}

    @mapping
    def parent_id(self, record):
        if not record.get('parent_id'):
            return
        binder = self.get_binder_for_model()
        category_id = binder.to_openerp(record['parent_id'], unwrap=True)
        mag_cat_id = binder.to_openerp(record['parent_id'])

        if category_id is None:
            raise MappingError("The product category with "
                               "magento id %s is not imported." %
                               record['parent_id'])
        return {'parent_id': category_id, 'magento_parent_id': mag_cat_id}
