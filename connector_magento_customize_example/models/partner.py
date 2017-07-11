# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging

from odoo import models, fields
from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping


_logger = logging.getLogger(__name__)


class MagentoResPartner(models.Model):
    _inherit = 'magento.res.partner'

    created_in = fields.Char(string='Created In', readonly=True)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    gender = fields.Selection(selection=[('male', 'Male'),
                                         ('female', 'Female'),
                                         ],
                              string='Gender')


# Pretend that Magento has the following IDs for the gender attribute
MAGENTO_GENDER = {'123': 'male',
                  '124': 'female'}


class PartnerImportMapper(Component):
    _inherit = 'magento.partner.import.mapper'

    @property
    def direct(self):
        mappings = super(PartnerImportMapper, self).direct[:]
        return mappings + [('created_in', 'created_in')]

    @mapping
    def gender(self, record):
        gender = MAGENTO_GENDER.get(record.get('gender'))
        return {'gender': gender}


class PartnerImporter(Component):
    _inherit = 'magento.partner.importer'

    def _after_import(self, partner_binding):
        super(PartnerImporter, self)._after_import(partner_binding)
        _logger.info('hello!')
