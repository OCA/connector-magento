# -*- encoding: utf-8 -*-
#########################################################################
#This module intergrates Open ERP with the magento core                 #
#Core settings are stored here                                          #
#########################################################################
#                                                                       #
# Copyright (C) 2009  Sharoon Thomas                                    #
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

import time
import xmlrpclib
import urllib2
import base64
from tools.translate import _


#NEW FEATURE

from openerp.osv.orm import Model
from openerp.osv.osv import except_osv
from openerp import tools
from base_external_referentials.decorator import only_for_referential
from base_external_referentials.decorator import open_report
from base_external_referentials.decorator import catch_error_in_report
import netsvc
import logging
_logger = logging.getLogger(__name__)

Model.mag_transform_and_send_one_resource = Model._transform_and_send_one_resource

@only_for_referential('magento', super_function = Model.mag_transform_and_send_one_resource)
@catch_error_in_report
def _transform_and_send_one_resource(self, cr, uid, external_session, *args, **kwargs):
    return self.mag_transform_and_send_one_resource(cr, uid, external_session, *args, **kwargs)

Model._transform_and_send_one_resource = _transform_and_send_one_resource


Model.mag_export_resources = Model._export_resources

@only_for_referential('magento', super_function = Model.mag_export_resources)
@open_report
def _export_resources(self, *args, **kwargs):
    return self.mag_export_resources( *args, **kwargs)
Model._export_resources = _export_resources


Model._mag_get_external_resource_ids = Model._get_external_resource_ids

@only_for_referential('magento', super_function = Model._get_external_resource_ids)
def _get_external_resource_ids(self, cr, uid, external_session, resource_filter=None, mapping=None, mapping_id=None, context=None):
    mapping, mapping_id = self._init_mapping(cr, uid, external_session.referential_id.id, mapping=mapping, mapping_id=mapping_id, context=context)
    ext_resource = mapping[mapping_id]['external_resource_name']
    search_method = mapping[mapping_id]['external_search_method']
    if not search_method:
        #TODO don't forget to replace model by name when name will be implemented
        raise except_osv(_('User Error'), _('There is not search method for the mapping %s')%(mapping[mapping_id]['model'],))
    return external_session.connection.call(search_method, [resource_filter])

Model._get_external_resource_ids = _get_external_resource_ids

Model._mag_get_external_resources = Model._get_external_resources

@only_for_referential('magento', super_function = Model._mag_get_external_resources)
def _get_external_resources(self, cr, uid, external_session, external_id=None, resource_filter=None, mapping=None, mapping_id=None, fields=None, context=None):
    mapping, mapping_id = self._init_mapping(cr, uid, external_session.referential_id.id, mapping=mapping, mapping_id=mapping_id, context=context)
    ext_resource = mapping[mapping_id]['external_resource_name']
    if external_id:
        read_method = mapping[mapping_id]['external_get_method']
        if not read_method:
            #TODO don't forget to replace model by nam ewhen name will be implemented
            raise except_osv(_('User Error'),
                _('There is no "Get Method" configured on the mapping %s') %
                mapping[mapping_id]['model'])
        return external_session.connection.call(read_method, [external_id])
    else:
        search_read_method = mapping[mapping_id]['external_list_method']
        if not search_read_method:
            #TODO don't forget to replace model by nam ewhen name will be implemented
            raise except_osv(_('User Error'),
                _('There is no "List Method" configured on the mapping %s') %
                mapping[mapping_id]['model'])
        return external_session.connection.call(search_read_method, [resource_filter or {}])

Model._get_external_resources = _get_external_resources

Model._mag_ext_create = Model.ext_create

@only_for_referential('magento', super_function = Model._mag_ext_create)
def ext_create(self, cr, uid, external_session, resources, mapping, mapping_id, context=None):
    ext_create_ids = {}
    main_lang = context['main_lang']
    for resource_id, resource in resources.items():
        ext_id = external_session.connection.call(mapping[mapping_id]['external_create_method'], [resource[main_lang]])
        ext_create_ids[resource_id] = ext_id
    return ext_create_ids

Model.ext_create = ext_create


Model._mag_ext_update= Model.ext_update
@only_for_referential('magento', super_function = Model._mag_ext_update)
def ext_update(self, cr, uid, external_session, resources, mapping=None, mapping_id=None, context=None):
    if not mapping[mapping_id]['external_update_method']:
        external_session.logger.warning(_("Not update method for mapping %s")%mapping[mapping_id]['model'])
        return False
    else:
        main_lang = context['main_lang']
        for resource_id, resource in resources.items():
            ext_id = resource[main_lang].pop('ext_id')
            ext_id = external_session.connection.call(mapping[mapping_id]['external_update_method'],
                                                                    [ext_id, resource[main_lang]])
    return True

Model.ext_update = ext_update

#@only_for_referential('magento', super_function = Model.send_to_external)
#def send_to_external(self, cr, uid, external_session, resource, update_date, context=None):
#    print 'send this data to the external system', update_date
#    print 'data', resource
#    self._set_last_exported_date(cr, uid, external_session, update_date, context=context)
#    import pdb; pdb.set_trace()
#    return True

#Model.send_to_external = send_to_external


#Model.ori_mag_init_context_before_exporting_resource = Model.init_context_before_exporting_resource

#@only_for_referential('magento', super_function = Model.init_context_before_exporting_resource)
#def init_context_before_exporting_resource(self, cr, uid, object_id, resource_name, context=None):
#    context = Model.ori_mag_init_context_before_exporting_resource(cr, uid, object_id, resource_name, context=context)
#    if self._name == 'external.referential':
#        referential = self.browse(cr, uid, object_id, context=context)
#    elif 'referential_id' in self._columns.keys():
#        referential = self.browse(cr, uid, object_id, context=context).referential_id

#    context['store_to_lang'] = {'default' : referential.default_lang_id.code}
#    if context.get('sale_shop_id'):
#        shop = self.pool.get('sale.shop').browse(cr, uid, context['sale.shop'], context=context)
#        for storeview in shop.storeview_ids:
#            if storeview.lang_id and storeview.lang_id.code != context['store_to_lang']['default']:
#                context['store_to_lang'][storeview.id] = storeview.lang_id.code
#    return context

#Model.init_context_before_exporting_resource = Model.init_context_before_exporting_resource


def ext_set_resource_as_imported(self, cr, uid, external_session, external_id, mapping=None, mapping_id=None, context=None):
    mapping, mapping_id = self._init_mapping(cr, uid, external_session.referential_id.id, mapping=mapping, mapping_id=mapping_id, context=context)
    done_method = mapping[mapping_id]['external_done_method']
    if done_method:
        return external_session.connection.call(done_method, [external_id])
    return False

Model.ext_set_resource_as_imported = ext_set_resource_as_imported

#DEPRECATED FEATURE!! YES ALL FUNCTION UNDER HIS LINE ARE DEPRECATED

#TODO clean error message, moreover it should be great to take a look on the magento python lib done by Sharoon : https://github.com/openlabs/magento

class Connection(object):
    def __init__(self, location, username, password, debug=False, logger=False):
        #Append / if not there
        if not location[-1] == '/':
            location += '/'
        self.corelocation = location
        #Please do not remove the str indeed xmlrpc lib require a string for the location
        #if an unicode is send it will raise you an error
        self.location = str(location + "index.php/api/xmlrpc")
        self.username = username
        self.password = password
        self.debug = debug
        self.result = {}
        self.logger = logger or _logger


    def connect(self):
        if not self.location[-1] == '/':
            self.location += '/'
        if self.debug:
            self.logger.info("Attempting connection with Settings:%s,%s,%s" % (self.location, self.username, self.password))
        self.ser = xmlrpclib.ServerProxy(self.location)
        for sleep_time in [1, 3, 6]:
            try:
                self.session = self.ser.login(self.username, self.password)
                if self.debug:
                    self.logger.info("Login Successful")
                return True
            except IOError, e:
                self.logger.error("Error in connecting:%s" % e)
                self.logger.warning("Webservice Failure, sleeping %s second before next attempt" % sleep_time)
                time.sleep(sleep_time)
            except Exception,e:
                self.logger.error("Magento Connection" + netsvc.LOG_ERROR +  "Error in connecting:%s" % e)
                self.logger.warning("Webservice Failure, sleeping %s second before next attempt" % sleep_time)
                time.sleep(sleep_time)
        raise except_osv(_('User Error'), _('Error when try to connect to magento, are your sure that your login is right? Did openerp can access to your magento?'))


    def call(self, method, *arguments):
        if arguments:
            arguments = list(arguments)[0]
        else:
            arguments = []
        for sleep_time in [1, 3, 6]:
            try:
                if self.debug:
                    self.logger.info(_("Calling Method:%s,Arguments:%s") % (method, arguments))
                res = self.ser.call(self.session, method, arguments)
                if self.debug:
                    if method=='catalog_product.list':
                        # the response of the method catalog_product.list can be very very long so it's better to see it only if debug log is activate
                        self.logger.debug(_("Query Returned:%s") % (res))
                    else:
                        self.logger.info(_("Query Returned:%s") % (res))
                return res
            except IOError, e:
                self.logger.error(_("Method: %s\nArguments:%s\nError:%s") % (method, arguments, e))
                self.logger.warning(_("Webservice Failure, sleeping %s second before next attempt") % (sleep_time))
                time.sleep(sleep_time)
        raise


    def fetch_image(self, imgloc):
        full_loc = self.corelocation + imgloc
        try:
            img = urllib2.urlopen(full_loc)
            return base64.b64encode(img.read())
        except Exception, e:
            pass

class MagerpModel(Model):
    _register = False # Set to false if the model shouldn't be automatically discovered.

    _MAGE_FIELD = 'magento_id'
    _MAGE_P_KEY = False
    _LIST_METHOD = False
    _GET_METHOD = False
    _CREATE_METHOD = False
    _UPDATE_METHOD = False
    _DELETE_METHOD = False
    _mapping = {}
    DEBUG = False

    #TODO deprecated, remove use
    def mage_to_oe(self, cr, uid, mageid, instance, *arguments):
        """given a record id in the Magento referential, returns a tuple (id, name) with the id in the OpenERP referential; Magento instance wise"""
        #Arguments as a list of tuple
        search_params = []
        if mageid:
            search_params = [(self._MAGE_FIELD, '=', mageid), ]
        if instance:
            search_params.append(('referential_id', '=', instance))
        for each in arguments:
            if not each:
                continue

            if isinstance(each, tuple):
                search_params.append(each)
            if isinstance(each, list):
                for each_tup in each:
                    search_params.append(each_tup)
        if search_params:
            oeid = self.search(cr, uid, search_params)
            if oeid:
                    read = self.read(cr, uid, oeid, [self._rec_name])
                    return (read[0]['id'], read[0][self._rec_name])
        return False

    #TODO deprecated, remove use
    def sync_import(self, cr, uid, magento_records, instance, debug=False, defaults=None, *attrs):

        if defaults is None:
            defaults = {}

        #Attrs of 0 should be mage2oe_filters
        if magento_records:
            mapped_keys = self._mapping.keys()
            mage2oe_filters = False
            if attrs:
                mage2oe_filters = attrs[0]
            for magento_record in magento_records:
                #Transform Record objects
                magento_record = self.cast_string(magento_record)
                #Check if record exists
                if mage2oe_filters:
                    rec_id = self.mage_to_oe(cr, uid, magento_record[self._MAGE_P_KEY], instance, mage2oe_filters)
                else:
                    if self._MAGE_P_KEY:
                        rec_id = self.mage_to_oe(cr, uid, magento_record[self._MAGE_P_KEY], instance)
                    else:
                        rec_id = False
                #Generate Vals
                vals = {}
                space = {
                    'self':self,
                    'uid':uid,
                    'rec_id':rec_id,
                    'cr':cr,
                    'referential_id':instance,
                    'temp_vars':{},
                    'mage2oe_filters':mage2oe_filters
                }

                #now properly mapp known Magento attributes to OpenERP entity columns:
                for each_valid_key in self._mapping:
                    if each_valid_key in magento_record.keys():
                        try:
                            if len(self._mapping[each_valid_key]) == 2 or self._mapping[each_valid_key][2] == False:#Only Name & type
                                vals[self._mapping[each_valid_key][0]] = self._mapping[each_valid_key][1](magento_record[each_valid_key]) or False
                            elif len(self._mapping[each_valid_key]) == 3:# Name & type & expr
                                #get the space ready for expression to run
                                #Add current type casted value to space if it exists or just the value
                                if self._mapping[each_valid_key][1]:
                                    space[each_valid_key] = self._mapping[each_valid_key][1](magento_record[each_valid_key]) or False
                                else:
                                    space[each_valid_key] = magento_record[each_valid_key] or False
                                space['vals'] = vals
                                exec self._mapping[each_valid_key][2] in space
                                if 'result' in space.keys():
                                    if self._mapping[each_valid_key][0]:
                                        vals[self._mapping[each_valid_key][0]] = space['result']
                                    else:
                                        #If mapping is a function return values is of type [('key','value')]
                                        if type(space['result']) == type([1, 2]) and space['result']:#Check type
                                            for each in space['result']:
                                                if type(each) == type((1, 2)) and each:#Check type
                                                    if len(each) == 2:#Assert length
                                                        vals[each[0]] = each[1]#Assign
                                else:
                                    if self._mapping[each_valid_key][0]:
                                        vals[self._mapping[each_valid_key][0]] = False
                        except Exception, e:
                            if self._mapping[each_valid_key][0]:#if not function mapping
                                vals[self._mapping[each_valid_key][0]] = magento_record[each_valid_key] or False
                vals['referential_id'] = instance
                tools.debug(vals)
                if self._MAGE_FIELD:
                    if self._MAGE_FIELD in vals.keys() and vals[self._MAGE_FIELD]:
                        self.record_save(cr, uid, rec_id, vals, defaults)
                else:
                    self.record_save(cr, uid, rec_id, vals, defaults)

    def record_save(self, cr, uid, rec_id, vals, defaults):
        if defaults:
            for key in defaults.keys():
                vals[key] = defaults[key]
        if rec_id:
            #Record exists, now update it
            self.write(cr, uid, rec_id[0], vals)
        else:
            #Record is not there, create it
            self.create(cr, uid, vals,)

    def cast_string(self, subject):
        """This function will convert string objects to the data type required. Example "0"/"1" to boolean conversion"""
        for key in subject.keys():
            if key[0:3] == "is_":
                if subject[key] == '0':
                    subject[key] = False
                else:
                    subject[key] = True
        return subject

    def mage_import_base(self,cr,uid,conn, external_referential_id, defaults=None, context=None):
        if context is None:
            context = {}
        if defaults is None:
            defaults = {}
        if not 'ids_or_filter' in context.keys():
            context['ids_or_filter'] = []
        result = {'create_ids': [], 'write_ids': []}
        mapping_id = self.pool.get('external.mapping').search(cr,uid,[('model','=',self._name),('referential_id','=',external_referential_id)])
        if mapping_id:
            data = []
            if context.get('id', False):
                get_method = self.pool.get('external.mapping').read(cr,uid,mapping_id[0],['external_get_method']).get('external_get_method',False)
                if get_method:
                    data = [conn.call(get_method, [context.get('id', False)])]
                    data[0]['external_id'] = context.get('id', False)
                    result = self.ext_import(cr, uid, data, external_referential_id, defaults, context)
            else:
                list_method = self.pool.get('external.mapping').read(cr,uid,mapping_id[0],['external_list_method']).get('external_list_method',False)
                if list_method:
                    data = conn.call(list_method, context['ids_or_filter'])

                    #it may happen that list method doesn't provide enough information, forcing us to use get_method on each record (case for sale orders)
                    if context.get('one_by_one', False):
                        self.mage_import_one_by_one(cr, uid, conn, external_referential_id, mapping_id[0], data, defaults, context)
                    else:
                        result = self.ext_import(cr, uid, data, external_referential_id, defaults, context)

        return result

    def mage_import_one_by_one(self, cr, uid, conn, external_referential_id, mapping_id, data, defaults=None, context=None):
        if context is None:
            context = {}
        result = {'create_ids': [], 'write_ids': []}
        if context.get('one_by_one', False):
            del(context['one_by_one'])
        for record in data:
            id = record[self.pool.get('external.mapping').read(cr, uid, mapping_id, ['external_key_name'])['external_key_name']]
            get_method = self.pool.get('external.mapping').read(cr, uid, mapping_id, ['external_get_method']).get('external_get_method',False)
            rec_data = [conn.call(get_method, [id])]
            rec_result = self.ext_import(cr, uid, rec_data, external_referential_id, defaults, context)
            result['create_ids'].append(rec_result['create_ids'])
            result['write_ids'].append(rec_result['write_ids'])
            # and let the import continue, because it will be imported on the next import
        return result

    def get_external_data(self, cr, uid, conn, external_referential_id, defaults=None, context=None):
        """Constructs data using WS or other synch protocols and then call ext_import on it"""
        return self.mage_import_base(cr, uid, conn, external_referential_id, defaults, context)#TODO refactor mage_import_base calls to this interface

    #TODO deprecated, remove use
    def mage_import(self, cr, uid, ids_or_filter, conn, instance, debug=False, defaults=None, *attrs):
        if defaults is None:
            defaults = {}

        if self._LIST_METHOD:
            magento_records = conn.call(self._LIST_METHOD, ids_or_filter)
            if attrs:
                self.sync_import(cr, uid, magento_records, instance, debug, defaults, attrs)
            else:
                self.sync_import(cr, uid, magento_records, instance, debug, defaults)
        else:
            raise except_osv(_('Undefined List method !'), _("list method is undefined for this object!"))

    #TODO deprecated, remove use
    def get_all_mage_ids(self, cr, uid, ids, instance=False):
        search_param = []
        if instance:
            search_param = [('referential_id', '=', instance)]
        if not ids:
            ids = self.search(cr, uid, search_param)
        reads = self.read(cr, uid, ids, [self._MAGE_FIELD])
        mageids = []
        for each in reads:
            mageids.append(each[self._MAGE_FIELD])
        return mageids

# deprecated, bw compat
magerp_osv = MagerpModel
