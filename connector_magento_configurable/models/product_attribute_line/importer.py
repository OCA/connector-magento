# -*- coding: utf-8 -*-
# Copyright 2017 Akretion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping
from odoo.addons.connector.exception import MappingError


class ProductAttributeLineBatchImporter(Component):
    """ Import the Magento Product Attribute Lines.
    """
    _name = 'magento.product.attribute.line.batch.importer'
    _inherit = 'magento.direct.batch.importer'
    _apply_on = ['magento.product.attribute.line']

    def attribute_code_field(self):
        """ allows to override the field where the attribute_code is stored"""
        return 'name'

    def _write_product(self, magento_product, tmpl_id, value_ids):
        old_tmpl_id = magento_product.product_tmpl_id.id
        magento_product.write(
            {'product_tmpl_id': tmpl_id,
             'attribute_value_ids': value_ids})
        self.env['product.template'].browse([old_tmpl_id]).unlink()

    def _get_magento_product_attribute_line(self,
                                            attribute, value, magento_product):
        line = {}
        line['attribute_id'] = attribute['odoo_id'][0]
        line['value_ids'] = [(4, value.odoo_id.id)]
        line['template_id'] = magento_product.odoo_id.product_tmpl_id.id
        line['attribute_name'] = attribute[self.attribute_code_field()]
        line['external_id'] = str(line['template_id'])
        line['external_id'] += '_'
        line['external_id'] += line['attribute_name']
        return line

    def _import_magento_product_attribute_line(self,
                                               record,
                                               attribute, value):
        line = self._get_magento_product_attribute_line(
            attribute,
            value,
            record
        )
        self._import_record(line)

    def get_updated_variants(self, record):
        """
            allows to easily override the field used (eg. external_id
            instead of defaul_code)
        """
        return self.backend_adapter.list_variants(record.external_id)

    def run(self, filters=None):
        """ Run the synchronization """
        record = filters['record']
        updated_variants = self.get_updated_variants(record)
        available_attributes = self.env[
            'magento.product.attribute'].search_read([], [
                self.attribute_code_field(),
                'odoo_id',
            ])
        value_binder = self.binder_for('magento.product.attribute.value')
        product_binder = self.binder_for('magento.product.product')
        for variant in updated_variants:
            magento_product = product_binder.to_internal(
                variant['entity_id'], unwrap=False)
            if not magento_product:
                raise MappingError("The product with "
                                   "magento id %s is not imported." %
                                   variant['entity_id'])
            attribute_value_ids = []
            for attribute in available_attributes:
                if variant.get(attribute[self.attribute_code_field()]):
                    value = value_binder.to_internal(
                        variant[attribute[self.attribute_code_field()]],
                        unwrap=False)
                    if not value:
                        raise MappingError("The product attribute value with "
                                           "magento id %s is not imported." %
                                           variant[attribute[
                                               self.attribute_code_field()
                                               ]])
                    self._import_magento_product_attribute_line(
                        record,
                        attribute,
                        value,
                    )
                    attribute_value_ids.append((4, value.odoo_id.id))
            if attribute_value_ids:
                self._write_product(
                    magento_product,
                    record.product_tmpl_id.id,
                    attribute_value_ids,
                    )


class ProductAttributeLineImporter(Component):
    _name = 'magento.product.attribute.line.importer'
    _inherit = 'magento.importer'
    _apply_on = ['magento.product.attribute.line']

    def _get_magento_data(self, storeview_id=None):
        """
        In this case,
        the magento_record already contains all the data to insert,
        no need to make a xmlrpc call
        """
        return self.magento_record

    def run(self, magento_record, force=False):
        self.magento_record = magento_record
        super(ProductAttributeLineImporter, self).run(
            magento_record['external_id'],
            force,
            )


class ProductAttributeLineImportMapper(Component):
    _name = 'magento.product.attribute.line.import.mapper'
    _inherit = 'magento.import.mapper'
    _apply_on = 'magento.product.attribute.line'

    direct = [
        ('value_ids', 'value_ids'),
    ]

    @mapping
    def product_tmpl_id(self, record):
        return {'product_tmpl_id': record['template_id']}

    @mapping
    def attribute_id(self, record):
        return {'attribute_id': record['attribute_id']}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}
