# -*- coding: utf-8 -*-

from openerp.osv import orm, fields
from openerp.addons.connector.unit.mapper import mapping
from openerp.addons.magentoerpconnect.product import ProductImportMapper
from openerp.addons.magentoerpconnect.backend import magento1700


class account_tax(orm.Model):
    _inherit = 'account.tax'

    _columns = {
        'magento_tax_id': fields.integer('Magento Tax ID'),
    }


@magento1700
class TaxProductImportMapper(ProductImportMapper):
    _model_name = 'magento.product.product'


    @mapping
    def tax_id(self, record):        
        tax_class_id = record.get('tax_class_id', '-1')       
        sess = self.session
        tax_ids = sess.search('account.tax',[('magento_tax_id','=',tax_class_id)])
        if tax_ids:        
            result = {'taxes_id': [(6, 0, tax_ids)]}
        else:
            result = {'taxes_id': []}
        return result
        