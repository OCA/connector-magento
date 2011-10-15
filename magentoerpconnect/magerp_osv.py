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

from osv import osv, fields
import time
import datetime
import xmlrpclib
import netsvc
import urllib2
import base64
from tools.translate import _


#TODO clean error message, moreover it should be great to take a look on the magento python lib done by Sharoon : https://github.com/openlabs/magento

class Connection(object):
    def __init__(self, location, username, password, debug=False):
        #Append / if not there
        if not location[-1] == '/':
            location += '/' 
        self.corelocation = location
        self.location = location + "index.php/api/xmlrpc"
        self.username = username
        self.password = password
        self.debug = True
        self.result = {}
        self.logger = netsvc.Logger()

    
    def connect(self):
        if not self.location[-1] == '/':
            self.location += '/'
        if self.debug:
            self.logger.notifyChannel(_("Magento Connection"), netsvc.LOG_INFO, _("Attempting connection with Settings:%s,%s,%s") % (self.location, self.username, self.password))
        self.ser = xmlrpclib.ServerProxy(self.location)
        for sleep_time in [1, 3, 6]:
            try:
                self.session = self.ser.login(self.username, self.password)
                if self.debug:
                    self.logger.notifyChannel(_("Magento Connection"), netsvc.LOG_INFO, _("Login Successful"))
                return True
            except IOError, e:
                self.logger.notifyChannel(_("Magento Connection"), netsvc.LOG_ERROR, _("Error in connecting:%s") % (e))
                self.logger.notifyChannel(_("Magento Call"), netsvc.LOG_WARNING, _("Webservice Failure, sleeping %s second before next attempt") % (sleep_time))
                time.sleep(sleep_time)
            except Exception,e:
                self.logger.notifyChannel(_("Magento Connection"), netsvc.LOG_ERROR, _("Error in connecting:%s") % (e))
                self.logger.notifyChannel(_("Magento Call"), netsvc.LOG_WARNING, _("Webservice Failure, sleeping %s second before next attempt") % (sleep_time))
                time.sleep(sleep_time)  
        raise osv.except_osv(_('User Error'), _('Error when try to connect to magento, are your sure that your login is right? Did openerp can access to your magento?'))

    
    def call(self, method, *arguments): 
        if arguments:
            arguments = list(arguments)[0]
        else:
            arguments = []
        for sleep_time in [1, 3, 6]:
            try:
                if self.debug:
                    self.logger.notifyChannel(_("Magento Connection"), netsvc.LOG_INFO, _("Calling Method:%s,Arguments:%s") % (method, arguments))
                res = self.ser.call(self.session, method, arguments)
                if self.debug:
                    if method=='catalog_product.list':
                        # the response of the method catalog_product.list can be very very long so it's better to see it only if debug log is activate
                        self.logger.notifyChannel(_("Magento Connection"), netsvc.LOG_DEBUG, _("Query Returned:%s") % (res))
                    else:
                        self.logger.notifyChannel(_("Magento Connection"), netsvc.LOG_INFO, _("Query Returned:%s") % (res))
                return res
            except IOError, e:
                self.logger.notifyChannel(_("Magento Call"), netsvc.LOG_ERROR, _("Method: %s\nArguments:%s\nError:%s") % (method, arguments, e))
                self.logger.notifyChannel(_("Magento Call"), netsvc.LOG_WARNING, _("Webservice Failure, sleeping %s second before next attempt") % (sleep_time))
                time.sleep(sleep_time)
        raise


    def fetch_image(self, imgloc):
        full_loc = self.corelocation + imgloc
        try:
            img = urllib2.urlopen(full_loc)
            return base64.b64encode(img.read())
        except Exception, e:
            pass

class magerp_osv(osv.osv):
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
    
    def external_connection(self, cr, uid, referential, DEBUG=False):
        if 'magento' in referential.type_id.name.lower():
            attr_conn = Connection(referential.location, referential.apiusername, referential.apipass, DEBUG)
            return attr_conn.connect() and attr_conn or False
        else:
            return super(magerp_osv, self).external_connection(cr, uid, referential, DEBUG=DEBUG)
    
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
            raise osv.except_osv(_('Undefined List method !'), _("list method is undefined for this object!"))
    
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
        
