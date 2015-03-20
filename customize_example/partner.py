# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2013-2015 Camptocamp SA
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

from openerp import models, fields
from openerp.addons.connector.unit.mapper import mapping
from openerp.addons.magentoerpconnect.partner import PartnerImportMapper
from .backend import magento_myversion


class magento_res_partner(models.Model):
    _inherit = 'magento.res.partner'

    created_in = fields.Char(string='Created In', readonly=True)


class res_partner(models.Model):
    _inherit = 'res.partner'

    gender = fields.Selection(selection=[('male', 'Male'),
                                         ('female', 'Female')],
                              string='Gender')


# Pretends that Magento has ID '123' for male and ID '124' for female.
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
