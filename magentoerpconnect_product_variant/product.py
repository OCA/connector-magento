# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright 2013
#    Author: Guewen Baconnier - Camptocamp SA
#            Chafique Delli - Akretion
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

from openerp.osv import orm
from openerp.addons.magentoerpconnect.backend import magento
from openerp.addons.magentoerpconnect_catalog.product import ProductProductExport
from openerp.addons.magentoerpconnect.product import ProductProductAdapter


class magento_product(orm.Model):
    _inherit = 'magento.product.product'
    
    def product_type_get(self, cr, uid, context=None):
        selection=super(magento_product, self).product_type_get(cr, uid, context=context)
        if ('configurable', 'Configurable Product') not in selection:
            selection += [('configurable', 'Configurable Product')]
        return selection
    
         
    _defaults = {
        'product_type': 'configurable',
        }



@magento(replacing=ProductProductExport)
class ProductProductExport(ProductProductExport):
    _model_name = ['magento.product.product']
    
    def _after_export(self):
        """ Export the link for the configurable product"""
        record = self.binding_record
        if record.is_display:
            if record.display_for_product_ids:
                product_obj = self.session.pool['magento.product.product']
                magento_product_ids=[]
                for axe in record.product_tmpl_id.axes_variance_ids:
                    if not record.openerp_id[axe.name]:
                        magento_axe=[]
                        attribute_obj = self.session.pool['magento.product.attribute']
                        magento_axe=attribute_obj.search(self.session.cr, self.session.uid,
                                                         [('openerp_id','=',axe.product_attribute_id.id)],
                                                         context=self.session.context)
                        magento_axe_id=attribute_obj.browse(self.session.cr, self.session.uid,
                                                            magento_axe[0],
                                                            context=self.session.context).magento_id
                        self.backend_adapter.setSuperAttributeValues(self.magento_id, magento_axe_id)
                for product in record.display_for_product_ids:
                    magento_product=product_obj.search(self.session.cr, self.session.uid,
                                                         [('openerp_id','=',product.id)],
                                                         context=self.session.context)
                    magento_product_id=product_obj.browse(self.session.cr, self.session.uid,
                                                            magento_product[0],
                                                            context=self.session.context).magento_id
                    magento_product_ids.append(magento_product_id)
                self.backend_adapter.assign(self.magento_id, magento_product_ids)
        
        
    
    #def _export_dependencies(self):
    #    """ Export the dependencies for the product"""
    #    super(ProductProductExport,self)._export_dependencies()
    #    return  
    
   
@magento(replacing=ProductProductAdapter)
class ProductProductAdapter(ProductProductAdapter):
    _model_name = ['magento.product.product']
       
    
    def setSuperAttributeValues(self, magento_id, magento_axe_id):
        """ Set Configurables Attributes """
        return self._call('ol_catalog_product_link.setSuperAttributeValues',
                          [magento_id, magento_axe_id])
    
    def assign(self, magento_id, magento_product_ids):
        """ Set product_super_link """
        return self._call('ol_catalog_product_link.assign',
                          [magento_id, magento_product_ids])



    



