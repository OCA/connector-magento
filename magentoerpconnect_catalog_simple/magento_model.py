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
from openerp import models, api, fields
from openerp.addons.magentoerpconnect.backend import magento
from openerp.addons.magentoerpconnect.unit.import_synchronizer import (
    import_batch,
    DirectBatchImporter,
    MagentoImporter
    )
from openerp.addons.magentoerpconnect.unit.binder import MagentoModelBinder
from openerp.addons.magentoerpconnect.unit.backend_adapter import (
    GenericAdapter)
from openerp.addons.connector.unit.mapper import ImportMapper, mapping
from openerp.addons.connector.session import ConnectorSession


class MagentoBackend(models.Model):
    _inherit = 'magento.backend'

    @api.multi
    def synchronize_metadata(self):
        super(MagentoBackend, self).synchronize_metadata()

        session = ConnectorSession.from_env(self.env)
        for backend in self:
            import_batch(session, 'magento.attribute.set', backend.id)

        return True


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

    # redefinir search
    def list(self):
        """ Search records according to some criteria
        and returns a list of ids

        :rtype: list
        """
        return self._call('%s.list' % self._magento_model, [])


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
class AttributeSetBinder(MagentoModelBinder):
    _model_name = [
        'magento.attribute.set'
    ]


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
