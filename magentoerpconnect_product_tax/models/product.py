# -*- coding: utf-8 -*-
# © 2016 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp.addons.connector.unit.mapper import mapping
from openerp.addons.magentoerpconnect.product import ProductImportMapper
from openerp.addons.magentoerpconnect.backend import magento

@magento(replacing=ProductImportMapper)
class TaxProductImportMapper(ProductImportMapper):
    _model_name = 'magento.product.product'

    @mapping
    def tax_id(self, record):
        tax_class_id = record.get('tax_class_id', '-1')
        tax = self.session.env['account.tax'].search(
            [('magento_tax_id', '=', tax_class_id)])
        result = {'taxes_id': [(6, 0, tax.ids)]}
        return result
