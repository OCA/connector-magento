# -*- encoding: utf-8 -*-
#########################################################################
#This module intergrates Open ERP with the magento core                 #
#Core settings are stored here                                          #
#########################################################################
#                                                                       #
# Copyright (C) 2009  Sharoon Thomas,                                   #
#                                                                       #
#This program is free software: you can redistribute it and/or modify   #
#it under the terms of the GNU General Public License as published by   #
#the Free Software Foundation, either version 3 of the License, or      #
#(at your option) any later version.                                    #
#                                                                       #
#This program is distributed in the hope that it will be useful,        #
#but WITHOUT ANY WARRANTY; without even the implied warranty of         #
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the          #
#GNU General Public License for more details.                           #
#                                                                       #
#You should have received a copy of the GNU General Public License      #
#along with this program.  If not, see <http://www.gnu.org/licenses/>.  #
#########################################################################
from osv import osv, fields
import magerp_osv
import mimetypes
import netsvc

class product_images(magerp_osv.magerp_osv):
    _inherit = "product.images"
    _columns = {
        'mage_file':fields.char('Magento File Name', size=100, readonly=True,
                                help="Filled when uploaded or synchronised"),
        'base_image':fields.boolean('Base Image'),
        'small_image':fields.boolean('Small Image'),
        'thumbnail':fields.boolean('Thumbnail'),
        'exclude':fields.boolean('Exclude'),
        'position':fields.integer('Position'),
        'sync_status':fields.boolean('Sync Status', readonly=True),
        'create_date': fields.datetime('Created date', readonly=True),
        'write_date': fields.datetime('Updated date', readonly=True),
    }
    _defaults = {
        'sync_status':lambda * a: False,
        'base_image':lambda * a:True,
        'small_image':lambda * a:True,
        'thumbnail':lambda * a:True,
        'exclude':lambda * a:False
    }
    
    def get_changed_ids(self, cr, uid, start_date=False):
        proxy = self.pool.get('product.images')
        domain = start_date and ['|', ('create_date', '>', start_date), ('write_date', '>', start_date)] or []
        return proxy.search(cr, uid, domain)
     
    def update_remote_images(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        logger = netsvc.Logger()
        conn = context.get('conn_obj', False)
        if not conn:
            return False

        def detect_types(image):
            types = []
            if image.small_image:
                types.append('small_image')
            if image.base_image:
                types.append('image')
            if image.thumbnail:
                types.append('thumbnail')
            return types

        def update_image(content, image):
            result = conn.call('catalog_product_attribute_media.update',
                               [image.product_id.magento_sku,
                                content,
                                {'label':image.name,
                                 'exclude':image.exclude,
                                 'types':detect_types(image),
                                }
                               ])
            return result

        logger.notifyChannel('ext synchro', netsvc.LOG_INFO, "Updating %s images" %(len(ids)))
        list_image = self.read(cr, uid, ids, ['write_date', 'create_date'], context=context)
        date_2_image={}
        image_2_date={}
        for image in list_image:
            date_2_image[image['write_date'] or image['create_date']] = image['id']
            image_2_date[image['id']] = image['write_date'] or image['create_date']
        list_date = date_2_image.keys()
        list_date.sort()
        
        ids = [date_2_image[date] for date in list_date]
        for each in self.browse_w_order(cr, uid, ids, context=context):
            if not each.product_id.magento_exportable:
                continue

            if each.mage_file: #If update
                result = update_image(each.mage_file, each)
                logger.notifyChannel('ext synchro', netsvc.LOG_INFO, "Updating %s's image: %s" %(each.product_id.magento_sku, each.name))
            else:
                if each.product_id.magento_sku:
                    logger.notifyChannel('ext synchro', netsvc.LOG_INFO, "Sending %s's image: %s" %(each.product_id.magento_sku, each.name))
                    result = conn.call('catalog_product_attribute_media.create',
                              [each.product_id.magento_sku,
                               {'file':{
                                        'name':each.name,
                                        'content':self.get_image(cr, uid, each.id),
                                        'mime':each.filename and mimetypes.guess_type(each.filename)[0] or 'image/jpeg',
                                        }
                               }
                               ])
                    self.write(cr, uid, each.id, {'mage_file':result})
                    result = update_image(result, each)
            self.pool.get('sale.shop').write(cr,uid,context['shop_id'],{'last_images_export_date':image_2_date[each.id]})
            cr.commit()
        return True
        
product_images()
