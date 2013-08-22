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
from openerp.addons.connector.exception import MappingError

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
    #           ('list_price', 'price'),
    #           ('description_sale', 'short_description'),
    #           ('default_code', 'sku'),
    #           ('product_type', 'type'),
    #           ('created_at', 'created_at'),
    #           ('updated_at', 'updated_at'),
    #           ('status', 'status'),
    #           ('visibility', 'visibility'),
    #           ('product_type', 'product_type')
    #           ]
    @mapping
    def all(self, record):
        return {'name': record.name,
                'description': record.description,
                'weight': record.weight,
                'price': record.list_price,
                'short_description': record.description_sale,
                'type': record.product_type,
                'created_at': record.created_at,
                'updated_at': record.updated_at,
                'status': record.status,
                'visibility': record.visibility,
                'product_type': record.product_type }

    @mapping
    def sku(self, record):
        sku = record.default_code
        if not sku:
            raise MappingError("The product attribute default code cannot be empty.")
        return {'sku': sku}

    @mapping
    def set(self, record):
        binder = self.get_binder_for_model('magento.product.attribute.set')
        set_id = binder.to_backend(record.attribute_set_id.id)
        return {'attrset': set_id}

    @mapping
    def tax(self, record):
        tax_class_id = record.tax_class if record.tax_class else 0
        return {'tax_class_id': tax_class_id}

    @mapping
    def website_ids(self, record):
        website_ids = []
        for website_id in record.website_ids:
            magento_id = website_id.magento_id
            website_ids.append(magento_id)
        return {'website_ids': website_ids}

    @mapping
    def category(self, record): 
        categ_ids = []
        if record.categ_id:
            for m_categ in record.categ_id.magento_bind_ids:
                if m_categ.backend_id.id == self.backend_record.id:
                    categ_ids.append(m_categ.magento_id) 

        for categ in record.categ_ids:
            for m_categ in categ.magento_bind_ids:
                if m_categ.backend_id.id == self.backend_record.id:
                    categ_ids.append(m_categ.magento_id)            
        return {'categories': categ_ids}
