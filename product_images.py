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
        if start_date:
            crids = self.pool.get('product.images').search(cr, uid, [('create_date', '>=', start_date)])
            wrids = self.pool.get('product.images').search(cr, uid, [('write_date', '>=', start_date)])
            for each in crids:
                if not each in wrids:
                    wrids.append(each)
            return wrids    #return one list of ids
        else:
            ids = self.pool.get('product.images').search(cr, uid, [])
            return ids
     
    def update_remote_images(self, cr, uid, ids, context={}):
        logger = netsvc.Logger()
        conn = context.get('conn_obj', False)
        if conn:
            for each in self.browse(cr, uid, ids):
                if each.product_id.magento_exportable:
                    if each.mage_file: #If update
                        types = []
                        if each.small_image:
                            types.append('small_image')
                        if each.base_image:
                            types.append('image')
                        if each.thumbnail:
                            types.append('thumbnail')
                        result = conn.call('catalog_product_attribute_media.update',
                                  [each.product_id.magento_sku,
                                   each.mage_file,
                                   {'label':each.name,
                                    'exclude':each.exclude,
                                    'types':types,
                                    }
                                   ])
                        #self.write(cr, uid, each.id, {'mage_file':result})
                    else:
                        if each.product_id.magento_sku:
                            logger.notifyChannel('ext synchro', netsvc.LOG_INFO, "Sending %s's image: %s" %(each.product_id.name, each.product_id.magento_sku))
                            result = conn.call('catalog_product_attribute_media.create',
                                      [each.product_id.magento_sku,
                                       {'file':{
                                                'content':self.get_image(cr, uid, each.id),
                                                'mime':each.filename and mimetypes.guess_type(each.filename)[0] or 'image/jpeg',
                                                }
                                       }
                                       ])
                            self.write(cr, uid, each.id, {'mage_file':result})
                            types = []
                            if each.small_image:
                                types.append('small_image')
                            if each.base_image:
                                types.append('image')
                            if each.thumbnail:
                                types.append('thumbnail')
                            new_result = conn.call('catalog_product_attribute_media.update',
                                      [each.product_id.magento_sku,
                                       result,
                                       {'label':each.name,
                                        'exclude':each.exclude,
                                        'types':types,
                                        }
                                       ])
                        #self.write(cr, uid, each.id, {'mage_file':new_result})
        else:
            return False
        return True
        
product_images()
