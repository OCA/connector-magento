# -*- coding: utf-8 -*-
# Copyright 2019 Callino
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from odoo import models, fields, api, _
from odoo.addons.component.core import Component
import urllib.request, urllib.parse, urllib.error
from urllib.parse import urljoin
import base64


_logger = logging.getLogger(__name__)

class MagentoProductMedia(models.Model):
    _inherit = 'magento.product.media'

    odoo_id = fields.Many2one('product.image', string="Product Image")


class ProductImage(models.Model):
    _inherit = 'product.image'

    magento_bind_ids = fields.One2many('magento.product.media', 'odoo_id', string="Magento Image")
