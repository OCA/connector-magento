# -*- coding: utf-8 -*-
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

from openerp.addons.magentoerpconnect.backend import magento
from openerp.addons.magentoerpconnect.unit.import_synchronizer import (
    DirectBatchImporter,
    MagentoImporter
    )
from openerp.addons.connector.unit.mapper import ImportMapper, mapping


@magento
class AttributeSetBatchImporter(DirectBatchImporter):
    """ Import the records directly, without delaying the jobs.

    Import the Attribute Set

    They are imported directly because this is a rare and fast operation,
    and we don't really bother if it blocks the UI during this time.
    (that's also a mean to rapidly check the connectivity with Magento).
    """
    _model_name = [
        'magento.attribute.set'
    ]

    def run(self, filters=None):
        """ Run the synchronization """
        records = self.backend_adapter.list()
        for record in records:
            importer = self.unit_for(MagentoImporter)
            importer.run(record['set_id'], record=record)


@magento
class AttributeSetMapper(ImportMapper):
    _model_name = 'magento.attribute.set'

    direct = [('name', 'name')]

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}


@magento
class AttributeSetImporter(MagentoImporter):
    _model_name = ['magento.attribute.set']

    def run(self, magento_id, force=False, record=None):
        """ Run the synchronization

        :param magento_id: identifier of the record on Magento
        """
        if record:
            self.magento_record = record
        return super(AttributeSetImporter, self).run(magento_id, force=force)

    def _get_magento_data(self):
        if self.magento_record:
            return self.magento_record
        else:
            return super(AttributeSetImporter, self)._get_magento_data()

#     def _import_dependencies(self):
#         """ Import the dependencies for the record"""
#         record = self.magento_record
#         self._import_dependency(record['group_id'],
#                                 'magento.res.partner.category')
