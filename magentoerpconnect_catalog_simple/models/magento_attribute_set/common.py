# -*- coding: utf-8 -*-
#
#
#    Author: Damien Crier
#    Copyright 2015 Camptocamp SA
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
#

from openerp import models, fields
from openerp.addons.magentoerpconnect.backend import magento
from openerp.addons.magentoerpconnect.unit.backend_adapter import (
    GenericAdapter)
from openerp.addons.magentoerpconnect.unit.binder import MagentoModelBinder


class MagentoAttributeSet(models.Model):
    _name = 'magento.attribute.set'
    _inherit = 'magento.binding'
    _description = 'Magento Attribute Set'

    name = fields.Char()


@magento
class AttributeSetAdapter(GenericAdapter):
    _model_name = 'magento.attribute.set'
    _magento_model = 'product_attribute_set'
#     _admin_path = 'system_store/editGroup/group_id/{id}'

    def list(self):
        """ Search records according to some criteria
        and returns a list of ids

        :rtype: list
        """
        return self._call('%s.list' % self._magento_model, [])


@magento
class AttributeSetBinder(MagentoModelBinder):
    _model_name = [
        'magento.attribute.set'
    ]
