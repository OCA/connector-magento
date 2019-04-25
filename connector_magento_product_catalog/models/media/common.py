# -*- coding: utf-8 -*-
# Copyright 2019 Callino
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from odoo import models, fields, api, _
from odoo.addons.component.core import Component
import urllib
from urlparse import urljoin
import base64


_logger = logging.getLogger(__name__)


class ProductMediaAdapter(Component):
    _inherit = 'magento.product.media.adapter'
    _magento2_name = 'entry'

    def _get_id_from_create(self, result, data=None):
        return result

    def _create_url(self, binding=None):
        def escape(term):
            if isinstance(term, basestring):
                return urllib.quote(term.encode('utf-8'), safe='')
            return term

        return 'products/%s/media' % (escape(binding.magento_product_id.external_id), )

    def _write_url(self, id, binding=None):
        def escape(term):
            if isinstance(term, basestring):
                return urllib.quote(term.encode('utf-8'), safe='')
            return term

        return 'products/%s/media/%s' % (escape(binding.magento_product_id.external_id), id)
