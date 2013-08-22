# -*- coding: utf-8 -*-

from openerp.osv import fields, orm, osv
from openerp.addons.connector.queue.job import job
from openerp.addons.connector.unit.mapper import (mapping,
                                                  changed_by,
                                                  ExportMapper)
from openerp.addons.magentoerpconnect.unit.delete_synchronizer import (
        MagentoDeleteSynchronizer)
from openerp.addons.magentoerpconnect.unit.export_synchronizer import (
        MagentoExporter)
from openerp.addons.magentoerpconnect.backend import magento
from openerp.addons.magentoerpconnect.product import ProductProductAdapter


@magento
class ProductProductDeleteSynchronizer(MagentoDeleteSynchronizer):
    """ Partner deleter for Magento """
    _model_name = ['magento.product.product']


@magento
class ProductProductExport(MagentoExporter):
    _model_name = ['magento.product.product']

@magento
class ProductProductExportMapper(ExportMapper):
    _model_name = 'magento.product.product'

    # direct = [('name', 'name'),
    #           ('description', 'description'),
    #           ('weight', 'weight'),
    #           ('standard_price', 'cost'),
    #           ('description_sale', 'short_description'),
    #           ('default_code', 'sku'),
    #           ('product_type', 'type'),
    #           ('created_at', 'created_at'),
    #           ('updated_at', 'updated_at'),
    #           ]

    @mapping
    def set(self, record):
        binder = self.get_binder_for_model('magento.product.attribute.set')
        set_id = binder.to_backend(record.attribute_set_id.id)
        return {'attrset': set_id}

    @mapping
    def category(self, record): 
        categ_ids = []
        binder = self.get_binder_for_model('magento.product.category')
        for categ in record.categ_ids:
            categ_id = binder.to_backend(categ.id)
            categ_ids.append(categ_id)

        return {
            'categories': categ_ids,
            'name': record.name,
            'description': record.description,
            'weight': record.weight,
            'price': record.list_price,
            'short_description': record.description,
            'sku': record.default_code,
            'product_type': record.product_type,
            'website_ids': [1],
            'status': 1,
            'visibility': 4,
            'tax_class_id':4,
            }