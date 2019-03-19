# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging
from odoo.addons.component.core import Component
from odoo import tools

_logger = logging.getLogger(__name__)


class AttributeValueImportMapper(Component):
    _name = 'magento.product.attribute.value.import.mapper'
    _inherit = 'magento.import.mapper'
    _apply_on = ['magento.product.attribute.value']

    direct = [
        ('label', 'name'),
        ('value', 'code')
    ]

    def finalize(self, map_record, values):
        if map_record.parent:
            # Fetch odoo attribute id - is required
            attribute_binder = self.binder_for(model='magento.product.attribute')
            magento_attribute = attribute_binder.to_internal(map_record.parent.source.get('attribute_id'), unwrap=False)
            # Generate ecxternal_id as attribute_id and code
            values.update({
                'external_id': "%s_%s" % (str(map_record.parent.source.get('attribute_id')), tools.ustr(values.get('code'))),
                'attribute_id': magento_attribute.odoo_id.id
            })
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

    def skip_item(self, map_record):
        """ Hook to implement in sub-classes when some child
        records should be skipped.

        The parent record is accessible in ``map_record``.
        If it returns True, the current child record is skipped.

        :param map_record: record that we are converting
        :type map_record: :py:class:`MapRecord`
        """
        return True if not map_record.source['value'] else False
