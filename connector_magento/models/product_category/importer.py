# Copyright 2013-2019 Camptocamp SA
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping
from odoo.addons.connector.exception import MappingError


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
            external_id, job_options=job_options
        )

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
            for node_id, children in list(tree.items()):
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
