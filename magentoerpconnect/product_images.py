# -*- encoding: utf-8 -*-
#########################################################################
#This module intergrates Open ERP with the magento core                 #
#Core settings are stored here                                          #
#########################################################################
#                                                                       #
# Copyright (C) 2009  Sharoon Thomas,                                   #
# Copyright (C) 2011 Akretion Sébastien BEAU sebastien.beau@akretion.com#
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
from tools.translate import _

#TODO the option small_image, thumbnail, exclude, base_image, should be store diferently indeed this is not compatible with mutli instance (maybe serialized will be a good solution)
#Moreover when a small is selected the flag on other image should be remove as magento does

class product_images(magerp_osv.magerp_osv):
    _inherit = "product.images"
    _columns = {
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
     
    def del_image_name(self, cr, uid, id, context=None):
        if context is None: context = {}
        image_ext_name_obj = self.pool.get('product.images.external.name')
        name_id = image_ext_name_obj.search(cr, uid, [('image_id', '=', id), ('external_referential_id', '=', context['external_referential_id'])], context=context)
        if name_id:
            return image_ext_name_obj.unlink(cr, uid, name_id, context=context)
        return False

    def update_remote_images(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        logger = netsvc.Logger()
        conn = context.get('conn_obj', False)
        if not conn:
            return False

        ir_model_data_obj = self.pool.get('ir.model.data')

        def detect_types(image):
            types = []
            if image.small_image:
                types.append('small_image')
            if image.base_image:
                types.append('image')
            if image.thumbnail:
                types.append('thumbnail')
            return types

        #TODO update the image file
        def update_image(image_name, image):
            result = conn.call('catalog_product_attribute_media.update',
                               [image.product_id.magento_sku,
                                image_name,
                                {'label':image.name,
                                 'exclude':image.exclude,
                                 'types':detect_types(image),
                                }
                               ])
            return result
        list_image = []
        list_image = self.read(cr, uid, ids, ['write_date', 'create_date'], context=context)

        date_2_image={}
        image_2_date={}
        for image in list_image:
            if date_2_image.get(image['write_date'] or image['create_date'], False):
                done = False
                count = 0
                while not done:
                    count += 1
                    if not date_2_image.get((image['write_date'] or image['create_date']) + '-' + str(count), False):
                        date_2_image[(image['write_date'] or image['create_date']) + '-' + str(count)] = image['id']
                        done = True
            else:
                date_2_image[image['write_date'] or image['create_date']] = image['id']
            image_2_date[image['id']] = image['write_date'] or image['create_date']
        list_date = date_2_image.keys()
        list_date.sort()
        
        ids = [date_2_image[date] for date in list_date]

        while ids:
            product_images = self.browse_w_order(cr, uid, ids[:1000], context=context)
            for each in product_images:
                need_to_be_created = True
                ext_file_name = each.oeid_to_extid(context['external_referential_id'])
                if ext_file_name: #If update
                    try:
                        logger.notifyChannel('ext synchro', netsvc.LOG_INFO, "Updating %s's image: %s" %(each.product_id.default_code, each.name))
                        result = update_image(ext_file_name, each)
                        logger.notifyChannel('ext synchro', netsvc.LOG_INFO, "%s's image updated with sucess: %s" %(each.product_id.default_code, each.name))
                        need_to_be_created = False
                    except Exception, e:
                        logger.notifyChannel(_("Magento Connection"), netsvc.LOG_ERROR, _("Error in connecting:%s") % (e))
                        if not "Fault 103" in str(e):
                            logger.notifyChannel(_("Magento Connection"), netsvc.LOG_ERROR, _("Unknow error stop export"))
                            raise
                        else:
                            #If the image was deleded in magento, the external name is automatically deleded before trying to re-create the image in magento
                            model_data_ids = ir_model_data_obj.search(cr, uid, [('model', '=', self._name), ('res_id', '=', each.id), ('external_referential_id', '=', context['external_referential_id'])])
                            if model_data_ids and len(model_data_ids) > 0:
                                ir_model_data_obj.unlink(cr, uid, model_data_ids, context=context)
                            logger.notifyChannel(_("Magento Connection"), netsvc.LOG_ERROR, _("The image don't exist in magento, try to create it"))
                if need_to_be_created:
                    if each.product_id.default_code:
                        logger.notifyChannel('ext synchro', netsvc.LOG_INFO, "Sending %s's image: %s" %(each.product_id.default_code, each.name))
                        result = conn.call('catalog_product_attribute_media.create',
                                  [each.product_id.default_code,
                                   {'file':{
                                            'name':each.name,
                                            'content': each.file,
                                            'mime': each.link and each.url and mimetypes.guess_type(each.url)[0] or each.extention and mimetypes.guess_type(each.extention)[0] or 'image/jpeg',
                                            }
                                   }
                                   ])
                        self.create_external_id_vals(cr, uid, each.id, result, context['external_referential_id'], context=context)
                        result = update_image(result, each)
                        logger.notifyChannel('ext synchro', netsvc.LOG_INFO, "%s's image send with sucess: %s" %(each.product_id.default_code, each.name))
                if image_2_date[each.id] > context['last_images_export_date']: #indeed if a product was created a long time ago and checked as exportable recently, the write date of the image can be far away in the past
                    self.pool.get('sale.shop').write(cr,uid,context['shop_id'],{'last_images_export_date':image_2_date[each.id]})
                cr.commit()
            ids = ids[1000:]
            logger.notifyChannel('ext synchro', netsvc.LOG_INFO, "still %s image to export" %len(ids))
        return True
        
product_images()
