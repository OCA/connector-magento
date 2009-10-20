from osv import osv, fields
import datetime
import xmlrpclib
import netsvc
import urllib2
import base64
from base_external_referentials import external_osv

class Connection():
    def __init__(self, location, username, password, debug=False):
        #Append / if not there
        if not location[-1] == '/':
            location += '/' 
        self.corelocation = location
        self.location = location + "index.php/api/xmlrpc"
        self.username = username
        self.password = password
        self.debug = debug
        self.result = {}
        self.logger = netsvc.Logger()
    
    def connect(self):
        if not self.location[-1] == '/':
            self.location += '/'
        if self.debug:
            self.logger.notifyChannel(_("Magento Connection"), netsvc.LOG_INFO, _("Attempting connection with Settings:%s,%s,%s") % (self.location, self.username, self.password))
        self.ser = xmlrpclib.ServerProxy(self.location)
        try:
            self.session = self.ser.login(self.username, self.password)
            if self.debug:
                self.logger.notifyChannel(_("Magento Connection"), netsvc.LOG_INFO, _("Login Successful"))
            return True
        except Exception, e:
            self.logger.notifyChannel(_("Magento Connection"), netsvc.LOG_ERROR, _("Error in connecting") % (e))
            raise
    
    def call(self, method, *args): 
        if args:
            arguments = list(args)[0]
        else:
            arguments = []
        try:
            if self.debug:
                self.logger.notifyChannel(_("Magento Connection"), netsvc.LOG_INFO, _("Calling Method:%s,Arguments:%s") % (method, arguments))
            res = self.ser.call(self.session, method, arguments)
            if self.debug:
                self.logger.notifyChannel(_("Magento Connection"), netsvc.LOG_INFO, _("Query Returned:%s") % (res))
            return res
        except Exception, e:
            self.logger.notifyChannel(_("Magento Call"), netsvc.LOG_ERROR, _("Method: %s\nArguments:%s\nError:%s") % (method, arguments, e))
            raise
    
    def fetch_image(self, imgloc):
        full_loc = self.corelocation + imgloc
        try:
            img = urllib2.urlopen(full_loc)
            return base64.b64encode(img.read())
        except Exception, e:
            pass

class magerp_osv(external_osv.external_osv):
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
        attr_conn = Connection(referential.location, referential.apiusername, referential.apipass, DEBUG)
        return attr_conn.connect() and attr_conn or False
        
    def mage_to_oe(self, cr, uid, mageid, instance, *args):
        """given a record id in the Magento referential, returns a tuple (id, name) with the id in the OpenERP referential; Magento instance wise"""
        #Arguments as a list of tuple
        search_params = []
        if mageid:
            search_params = [(self._MAGE_FIELD, '=', mageid), ]
        if instance:
            search_params.append(('instance', '=', instance))
        for each in args:
            if each:
                if type(each) == type((1, 2)):
                    search_params.append(each)
                if type(each) == type([1, 2]):
                    for each_tup in each:
                        search_params.append(each_tup)
        if search_params:
            oeid = self.search(cr, uid, search_params)
            if oeid:
                    read = self.read(cr, uid, oeid, [self._rec_name])
                    return (read[0]['id'], read[0][self._rec_name])
        return False
    
    def sync_import(self, cr, uid, magento_records, instance, debug=False, defaults={}, *attrs):
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
                            'instance':instance,
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
                vals['instance'] = instance
                if debug:
                    print vals
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
    
    def mage_import_base(self,cr,uid,conn, external_referential_id, defaults={}, context={}):
        if not 'ids_or_filter' in context.keys():
            context['ids_or_filter'] = []
        result = {'create_ids': [], 'write_ids': []}
        mapping_id = self.pool.get('external.mapping').search(cr,uid,[('model','=',self._name),('referential_id','=',external_referential_id)])
        if mapping_id:
            list_method = self.pool.get('external.mapping').read(cr,uid,mapping_id[0],['external_list_method']).get('external_list_method',False)
            if list_method:
                data = conn.call(list_method, context['ids_or_filter'])
                result = self.ext_import(cr, uid, data, external_referential_id, defaults, context)
        return result
                
    def mage_import(self, cr, uid, ids_or_filter, conn, instance, debug=False, defaults={}, *attrs):
        if self._LIST_METHOD:
            magento_records = conn.call(self._LIST_METHOD, ids_or_filter)
            if attrs:
                self.sync_import(cr, uid, magento_records, instance, debug, defaults, attrs)
            else:
                self.sync_import(cr, uid, magento_records, instance, debug, defaults)
        else:
            raise osv.except_osv(_('Undefined List method !'), _("list method is undefined for this object!"))

    def mage_export(self, cr, uid, ids, conn, instance, context={}, debug=False):
        for record_read in self.read(cr, uid, ids, [self._MAGE_FIELD]):#we might imagine a faster batch update to be developed later on eventually
            if record_read[self._MAGE_FIELD]:
                self.mage_export_update(cr, uid, [record_read["id"]], conn, instance, context={})
            else:
                self.mage_export_create(cr, uid, [record_read["id"]], conn, instance, context={})
                
    def mage_export_create(self, cr, uid, ids, conn, instance, context={}):
        mage_records = self.oe_record_to_mage_create(cr, uid, ids, conn, instance, context) #FIXME: eventually that array might be very large, split it into reasonable chunks?
        for mage_record in mage_records:#we might imagine a faster batch update to be developed later on eventually
            mage_id = conn.call(self._CREATE_METHOD, mage_record[1])
            self.write(cr, uid, mage_record[0], {self._MAGE_FIELD: mage_id})
            cr.commit();#better to commit while export being made in case of slow upload to Magento crashing
            #TODO log it?
    
    def mage_export_update(self, cr, uid, ids, conn, instance, context={}):
        mage_records = self.oe_record_to_mage_update(cr, uid, ids, conn, instance, context) #FIXME: eventually that array might be very large, split it into reasonable chunks?
        for mage_record in mage_records:#we might imagine a faster batch update to be developed later on eventually
            mage_id = conn.call(self._UPDATE_METHOD, mage_record[1])
            self.write(cr, uid, mage_record[0], {self._MAGE_FIELD: mage_id})
            cr.commit();#better to commit while export being made in case of slow upload to Magento crashing
            #TODO log it?
    
    def oe_record_to_mage_create(self, cr, uid, ids, conn, instance, context={}):
        raise "oe_record_to_mage conversion method not complemented for that class"
    
    def oe_record_to_mage_update(self, cr, uid, ids, conn, instance, context={}):
        raise "oe_record_to_mage conversion method not complemented for that class"
    
    def oe_record_to_mage_data(self, cr, uid, oe_product, conn, instance, context={}):
        raise "oe_record_to_mage_data method not complemented for that class"
    
    def get_all_mage_ids(self, cr, uid, ids=[], instance=False):
        search_param = []
        if instance:
            search_param = [('instance', '=', instance)]
        if not ids:
            ids = self.search(cr, uid, search_param)
        reads = self.read(cr, uid, ids, [self._MAGE_FIELD])
        mageids = []
        for each in reads:
            mageids.append(each[self._MAGE_FIELD])
        return mageids
        
