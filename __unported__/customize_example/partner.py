# -*- coding: utf-8 -*-

from openerp.osv import orm, fields
from openerp.addons.connector.unit.mapper import mapping
from openerp.addons.magentoerpconnect.partner import PartnerImportMapper
from .backend import magento_myversion


class magento_res_partner(orm.Model):
    _inherit = 'magento.res.partner'

    _columns = {
        'created_in': fields.char('Created In', readonly=True),
        }


class res_partner(orm.Model):
    _inherit = 'res.partner'

    _columns = {
        'gender': fields.selection([('male', 'Male'),
                                    ('female', 'Female')],
                                   string='Gender'),
        }


MAGENTO_GENDER = {'123': 'male',
                  '124': 'female'}


@magento_myversion
class MyPartnerImportMapper(PartnerImportMapper):
    _model_name = 'magento.res.partner'

    direct = PartnerImportMapper.direct + [('created_in', 'created_in')]

    @mapping
    def gender(self, record):
        gender = MAGENTO_GENDER.get(record.get('gender'))
        return {'gender': gender}
