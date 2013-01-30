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
import mimetypes

from openerp.osv.orm import Model
from openerp.osv import fields
from openerp.tools.translate import _

from .magerp_osv import MagerpModel
from base_external_referentials.decorator import commit_now
from base_external_referentials.decorator import only_for_referential

#TODO Option on image should be compatible with multi-referential
#Indeed when you have two Magento maybe you do not want to use the
#same image for the base_image, thumbnail ot small_image
#Maybe the solution will to use a serialized field that store the
#value for each referential

#TODO As only one image can be a small_image, thumbnail or base_image
#We should add some constraint or automatically remove the flag on the
#other image of the product.

#TODO refactor all of this code and use the generic function from
#base_external_referentials.

class product_images(MagerpModel):
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
        name_id = image_ext_name_obj.search(cr, uid, [('image_id', '=', id), ('external_referential_id', '=', context['referential_id'])], context=context)
        if name_id:
            return image_ext_name_obj.unlink(cr, uid, name_id, context=context)
        return False



    @only_for_referential(ref_categ ='Multichannel Sale')
    def _get_last_exported_date(self, cr, uid, external_session, context=None):
        shop = external_session.sync_from_object
        return shop.last_images_export_date

    @only_for_referential(ref_categ ='Multichannel Sale')
    @commit_now
    def _set_last_exported_date(self, cr, uid, external_session, date, context=None):
        shop = external_session.sync_from_object
        return self.pool.get('sale.shop').write(cr, uid, shop.id, {'last_images_export_date': date}, context=context)



    def update_remote_images(self, cr, uid, external_session, ids, context=None):
        if context is None:
            context = {}

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
        def update_image(product_extid, image_name, image):
            result = external_session.connection.call('catalog_product_attribute_media.update',
                               [product_extid,
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
                product_extid = each.product_id.get_extid(external_session.referential_id.id)
                if not product_extid:
                    external_session.logger.info("The product %s do not exist on magento" %(each.product_id.default_code))
                else:
                    need_to_be_created = True
                    ext_file_name = each.get_extid(external_session.referential_id.id)
                    if ext_file_name: #If update
                        try:
                            external_session.logger.info("Updating %s's image: %s" %(each.product_id.default_code, each.name))
                            result = update_image(product_extid, ext_file_name, each)
                            external_session.logger.info("%s's image updated with sucess: %s" %(each.product_id.default_code, each.name))
                            need_to_be_created = False
                        except Exception, e:
                            external_session.logger.error(_("Error in connecting:%s") % (e))
                            if not "Fault 103" in str(e):
                                external_session.logger.error(_("Unknow error stop export"))
                                raise
                            else:
                                #If the image was deleded in magento, the external name is automatically deleded before trying to re-create the image in magento
                                model_data_ids = ir_model_data_obj.search(cr, uid, [('model', '=', self._name), ('res_id', '=', each.id), ('referential_id', '=', external_session.referential_id.id)])
                                if model_data_ids and len(model_data_ids) > 0:
                                    ir_model_data_obj.unlink(cr, uid, model_data_ids, context=context)
                                external_session.logger.error(_("The image don't exist in magento, try to create it"))
                    if need_to_be_created:
                        if each.product_id.default_code:
                            pas_ok = True
                            suceed = False
                            external_session.logger.info("Sending %s's image: %s" %(each.product_id.default_code, each.name))
                            data = {
                                'file':{
                                    'name':each.name,
                                    'content': each.file,
                                    'mime': each.link and each.url and mimetypes.guess_type(each.url)[0] \
                                            or each.extention and mimetypes.guess_type(each.name + each.extention)[0] \
                                            or 'image/jpeg',
                                    }
                            }
                            result = external_session.connection.call('catalog_product_attribute_media.create', [product_extid, data, False, 'id'])

                            self.create_external_id_vals(cr, uid, each.id, result, external_session.referential_id.id, context=context)
                            result = update_image(product_extid, result, each)
                            external_session.logger.info("%s's image send with sucess: %s" %(each.product_id.default_code, each.name))


                if context.get('last_images_export_date') and image_2_date[each.id] > context['last_images_export_date']: #indeed if a product was created a long time ago and checked as exportable recently, the write date of the image can be far away in the past
                    self._set_last_exported_date(cr, uid, external_session, image_2_date[each.id], context=context)
                cr.commit()
            ids = ids[1000:]
            external_session.logger.info("still %s image to export" %len(ids))
        return True
