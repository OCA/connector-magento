# -*- coding: utf-8 -*-

from openerp.osv import fields, orm, osv
from openerp.addons.connector.unit.mapper import (mapping,
                                                  changed_by,
                                                  ExportMapper)
from openerp.addons.magentoerpconnect.unit.delete_synchronizer import (
        MagentoDeleteSynchronizer)
from openerp.addons.magentoerpconnect.unit.export_synchronizer import (
        MagentoExporter)
from openerp.addons.magentoerpconnect.backend import magento
from openerp.addons.magentoerpconnect.product_category import ProductCategoryAdapter

@magento
class ProductCategoryDeleteSynchronizer(MagentoDeleteSynchronizer):
    """ Partner deleter for Magento """
    _model_name = ['magento.product.category']


@magento
class ProductCategoryExport(MagentoExporter):
    _model_name = ['magento.product.category']

@magento
class ProductCategoryExportMapper(ExportMapper):
    _model_name = 'magento.product.category'

    direct = [('description', 'description'),
    		  ('name', 'name'), #change that to mapping top level category has no name
             ]
    @mapping
    def sort(self, record):
        return {'default_sort_by':'price', 'available_sort_by': 'price'}

    @mapping
    def parent(self, record):
        """ Magento root category's Id equals 1 """
        parent_id = record.magento_parent_id.magento_id
        if not parent_id:
            parent_id = 1
        return {'parent_id':parent_id}

    @mapping
    def active(self, record):
        is_active = record['is_active']
        if not is_active:
            is_active = 0
        return {'is_active':is_active}

    @mapping
    def menu(self, record):
        include_in_menu = record['include_in_menu']
        if not include_in_menu:
            include_in_menu = 0
        return {'include_in_menu':include_in_menu}