# -*- coding: utf-8 -*-
# Copyright 2019 Callino
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from odoo import models, fields, api, _
from odoo.addons.component.core import Component
import urllib
from urlparse import urljoin
import base64
import uuid


_logger = logging.getLogger(__name__)


class MagentoProductMedia(models.Model):
    _name = 'magento.product.media'
    _inherit = 'magento.binding'
    _description = 'Magento Product Media'
    _order = 'position'

    @api.depends('backend_id', 'file')
    def _compute_url(self):
        for media in self:
            media.url = urljoin(media.backend_id.location, "/pub/media/catalog/product%s" % media.file)

    @api.depends('url')
    def _get_image(self):
        for media in self:
            f = urllib.urlopen(media.url)
            if f.code == 200:
                media.image = base64.b64encode(f.read())
            f.close()

    magento_product_id = fields.Many2one(comodel_name='magento.product.product',
                                         string='Magento Product',
                                         required=False,
                                         ondelete='cascade')
    magento_product_tmpl_id = fields.Many2one(comodel_name='magento.product.template',
                                              string='Magento Product Template',
                                              required=False,
                                              ondelete='cascade')
    label = fields.Char(string="Label")
    type = fields.Selection([
        ('product_image', 'Product Image'),
        ('product_image_ids', 'Extra Product Images'),
    ], string='Type')
    file = fields.Char(string="File", required=True)
    url = fields.Char(string="URL", compute='_compute_url', store=False)
    image = fields.Binary(string="Image", compute='_get_image')
    position = fields.Integer(string="Position", default=0)
    disabled = fields.Boolean(string="Disabled", default=False)
    mimetype = fields.Char(string="Mimetype", required=True, default='image/jpeg')
    media_type = fields.Selection([
        ('image', _(u'Image')),
        ('external-video', _(u'External Video')),
    ], default='image', string='Media Type')
    image_type_image = fields.Boolean(string="Image", default=False)
    image_type_small_image = fields.Boolean(string="Small Image", default=False)
    image_type_thumbnail = fields.Boolean(string="Thumbnail", default=False)
    image_type_swatch = fields.Boolean(string="Swatch", default=False)

    _sql_constraints = [
        ('file_uniq', 'unique(backend_id, magento_product_id, file)',
         'The filename must be unique.'),
    ]

    @api.model
    def create(self, vals):
        if 'magento_product_id' in vals and vals['magento_product_id']:
            existing = self.search_count([
                ('backend_id', '=', vals['backend_id']),
                ('magento_product_id', '=', vals['magento_product_id']),
                ('file', '=', vals['file']),
            ])
        elif 'magento_product_tmpl_id' in vals and vals['magento_product_tmpl_id']:
            existing = self.search_count([
                ('backend_id', '=', vals['backend_id']),
                ('magento_product_tmpl_id', '=', vals['magento_product_tmpl_id']),
                ('file', '=', vals['file']),
            ])
        if existing:
            extension = 'png' if vals['mimetype']=='image/png' else 'jpeg'
            vals['file'] = "%s.%s" % (uuid.uuid4(), extension)
        return super(MagentoProductMedia, self).create(vals)


class ProductTemplate(models.Model):
    _inherit = 'magento.product.template'

    magento_image_bind_ids = fields.One2many(
        comodel_name='magento.product.media',
        inverse_name='magento_product_tmpl_id',
        string='Magento Images',
    )


class MagentoProductProduct(models.Model):
    _inherit = 'magento.product.product'

    magento_image_bind_ids = fields.One2many(
        comodel_name='magento.product.media',
        inverse_name='magento_product_id',
        string='Magento Images',
    )


class ProductMediaAdapter(Component):
    _name = 'magento.product.media.adapter'
    _inherit = 'magento.adapter'
    _apply_on = 'magento.product.media'
    _magento2_key = 'entry_id'

    def _read_url(self, id, sku):
        def escape(term):
            if isinstance(term, basestring):
                return urllib.quote(term.encode('utf-8'), safe='')
            return term

        return 'products/%s/media/%s' % (escape(sku), id)

    def read(self, id, sku, attributes=None, storeview_code=None, binding=None):
        if self.work.magento_api._location.version == '2.0':
            return self._call(self._read_url(id, sku), None, storeview=storeview_code)

