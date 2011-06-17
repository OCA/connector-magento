#########################################################################
#                                                                       #
# Copyright (C) 2011 Openlabs Technologies & Consulting (P) Ltd.        #
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

from osv import osv
import netsvc
class sale_order(osv.osv):
    _inherit = "sale.order"
    
    def ext_import(self, cr, uid, data, external_referential_id, defaults=None, context=None):
        if defaults is None:
            defaults = {}
        if context is None:
            context = {}

        #Inward data has to be list of dictionary
        #This function will import a given set of data as list of dictionary into Open ERP
        write_ids = []  #Will record ids of records modified, not sure if will be used
        create_ids = [] #Will record ids of newly created records, not sure if will be used
        logger = netsvc.Logger()
        if data:
            mapping_id = self.pool.get('external.mapping').search(cr, uid, [('model', '=', self._name), ('referential_id', '=', external_referential_id)])
            if mapping_id:
                #If a mapping exists for current model, search for mapping lines
                mapping_line_ids = self.pool.get('external.mapping.line').search(cr, uid, [('mapping_id', '=', mapping_id), ('type', 'in', ['in_out', 'in'])])
                mapping_lines = self.pool.get('external.mapping.line').read(cr, uid, mapping_line_ids, ['external_field', 'external_type', 'in_function'])
                if mapping_lines:
                    #if mapping lines exist find the data conversion for each row in inward data
                    for_key_field = self.pool.get('external.mapping').read(cr, uid, mapping_id[0], ['external_key_name'])['external_key_name']
                    for each_row in data:
                        vals = self.oevals_from_extdata(cr, uid, external_referential_id, each_row, for_key_field, mapping_lines, defaults, context)
                        #perform a record check, for that we need foreign field
                        external_id = vals.get(for_key_field, False) or each_row.get(for_key_field, False) or each_row.get('external_id', False)
                        #del vals[for_key_field] looks like it is affecting the import :(
                        #Check if record exists
                        existing_ir_model_data_id = self.pool.get('ir.model.data').search(cr, uid, [('model', '=', self._name), ('name', '=', self.prefixed_id(external_id)), ('external_referential_id', '=', external_referential_id)])
                        record_test_id = False
                        if existing_ir_model_data_id:
                            existing_rec_id = self.pool.get('ir.model.data').read(cr, uid, existing_ir_model_data_id, ['res_id'])[0]['res_id']

                            #Note: OpenERP cleans up ir_model_data which res_id records have been deleted only at server update because that would be a perf penalty,
                            #so we take care of it here:
                            record_test_id = self.search(cr, uid, [('id', '=', existing_rec_id)])
                            if not record_test_id:
                                self.pool.get('ir.model.data').unlink(cr, uid, existing_ir_model_data_id)

                        if record_test_id:
                            # If the sale order already exists then just skip the order
                            # It was too performance costly to create subclass and call super function
                            continue

                        else:
                            crid = self.oe_create(cr, uid, vals, each_row, external_referential_id, defaults, context)
                            create_ids.append(crid)
                            ir_model_data_vals = {
                                'name': self.prefixed_id(external_id),
                                'model': self._name,
                                'res_id': crid,
                                'external_referential_id': external_referential_id,
                                'module': 'extref/' + self.pool.get('external.referential').read(cr, uid, external_referential_id, ['name'])['name']
                            }
                            self.pool.get('ir.model.data').create(cr, uid, ir_model_data_vals)
                            logger.notifyChannel('ext synchro', netsvc.LOG_INFO, "Created in OpenERP %s from External Ref with external_id %s and OpenERP id %s successfully" %(self._name, external_id, crid))
                        cr.commit()

        return {'create_ids': create_ids, 'write_ids': write_ids}
    
sale_order()
