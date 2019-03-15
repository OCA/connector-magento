# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging
from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import (
    mapping, 
    only_create, 
    ImportMapChild
    )
import uuid

_logger = logging.getLogger(__name__)


class AttributeValueImportMapper(Component):
    _name = 'magento.product.attribute.value.import.mapper'
    _inherit = 'magento.import.mapper'
    _apply_on = ['magento.product.attribute.value']

    direct = [
        ('value', 'code'),
    ]

    @mapping
    def get_value(self, record):
        name = record['label'] or False
        if not name:
            name = u'False'
        return {'name': name}

    @mapping
    def get_external_id(self, record):
        if record.get('value_index'):
            return {'external_id': record.get('value_index')}
        if record.get('value'):
            return {'external_id': record.get('value')}
        # No external id available ? we do need something here - so just generate a uuid4
        return {'external_id': str(uuid.uuid4())}

    def finalize(self, map_record, values):
        if map_record.parent:
            external_id = str(values.get('external_id'))
            external_id_parent = str(map_record.parent.source.get('attribute_id'))
            values.update({'external_id': external_id_parent + '_' + external_id })
            # Search for existing entry
            binder = self.binder_for(model='magento.product.attribute.value')
            magento_value = binder.to_internal(values['external_id'], unwrap=False)
            if magento_value:
                values.update({'id': magento_value.id})
        return values


class AttributeValueMapChild(Component):
    _name = 'magento.product.attribute.value.map.child.import'
    _inherit = 'base.map.child.import'
    _apply_on = ['magento.product.attribute.value']

    def format_items(self, items_values):
        """ Format the values of the items mapped from the child Mappers.

        It can be overridden for instance to add the Odoo
        relationships commands ``(6, 0, [IDs])``, ...

        As instance, it can be modified to handle update of existing
        items: check if an 'id' has been defined by
        :py:meth:`get_item_values` then use the ``(1, ID, {values}``)
        command

        :param items_values: list of values for the items to create
        :type items_values: list

        """
        res = []
        for values in items_values:
            if 'id' in values:
                id = values.pop('id')
                res.append((1, id, values))
            else:
                res.append((0, 0, values))
        return res
