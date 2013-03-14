# -*- coding: utf-8 -*-
#########################################################################
#This module intergrates Open ERP with the magento core                 #
#Core settings are stored here                                          #
#########################################################################
#                                                                       #
# Copyright (C) 2011-2013 Akretion   Sébastien Beau                     #
# Copyright (C) 2011-2013 Camptocamp Guewen Baconnier                   #
#                                                                       #
#This program is free software: you can redistribute it and/or modify   #
#it under the terms of the GNU General Public License as published by   #
#the Free Software Foundation, either version 3 of the License, or      #
#(at your option) any later version.                                    #
#                                                                       #
#This program is distributed in the hope that it will be useful,        #
#but WITHOUT ANY WARRANTY; without even the implied warranty of         #
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the          #
#GNU General Public License for more details.                           #
#                                                                       #
#You should have received a copy of the GNU General Public License      #
#along with this program.  If not, see <http://www.gnu.org/licenses/>.  #
#########################################################################

import logging
from datetime import datetime

from openerp.osv import fields, orm


from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
import openerp.addons.connector as connector
from openerp.addons.connector.session import ConnectorSession
from .unit.import_synchronizer import import_batch, import_partners_since

_logger = logging.getLogger(__name__)


class magento_backend(orm.Model):
    _name = 'magento.backend'
    _doc = 'Magento Backend'
    _inherit = 'connector.backend'

    _backend_type = 'magento'

    def _select_versions(self, cr, uid, context=None):
        """ Available versions

        Can be inherited to add custom versions.
        """
        return [('1.5', '1.5'),
                ('1.7', '1.7')]

    _columns = {
        'version': fields.selection(
            _select_versions,
            string='Version',
            required=True),
        'location': fields.char('Location'),
        'username': fields.char('Username'),
        'password': fields.char('Password'),
        'default_lang_id': fields.many2one(
                'res.lang',
                'Default Language',
                help="Choose the language which will be used for the "
                     "Default Value in Magento"),

        # add a field `auto_activate` -> activate a cron
        'import_partners_since': fields.datetime('Import partners since'),
        'import_products_since': fields.datetime('Import products since'),
    }

    def synchronize_metadata(self, cr, uid, ids, context=None):
        if not hasattr(ids, '__iter__'):
            ids = [ids]
        session = ConnectorSession(cr, uid, context=context)
        for backend_id in ids:
            for model in ('magento.website',
                          'magento.store',
                          'magento.storeview'):
                # import directly, do not delay because this
                # is a fast operation, a direct return is fine
                # and it is simpler to import them sequentially
                import_batch(session, model, backend_id)

        return True

    def import_partners_since(self, cr, uid, ids, context=None):
        if not hasattr(ids, '__iter__'):
            ids = [ids]
        session = ConnectorSession(cr, uid, context=context)
        for backend_record in self.browse(cr, uid, ids, context=context):
            since_date = None
            if backend_record.import_partners_since:
                since_date = datetime.strptime(
                        backend_record.import_partners_since,
                        DEFAULT_SERVER_DATETIME_FORMAT)
            import_partners_since.delay(session, 'magento.res.partner',
                                        backend_record.id,
                                        since_date=since_date)

        return True

    def import_customer_groups(self, cr, uid, ids, context=None):
        if not hasattr(ids, '__iter__'):
            ids = [ids]
        session = ConnectorSession(cr, uid, context=context)
        for backend_id in ids:
            import_batch.delay(session, 'magento.res.partner.category',
                               backend_id)

        return True

    def import_product_categories(self, cr, uid, ids, context=None):
        if not hasattr(ids, '__iter__'):
            ids = [ids]
        session = ConnectorSession(cr, uid, context=context)
        for backend_id in ids:
            import_batch.delay(session, 'magento.product.category',
                               backend_id)
        return True

    def import_product_product(self, cr, uid, ids, context=None):
        if not hasattr(ids, '__iter__'):
            ids = [ids]
        session = ConnectorSession(cr, uid, context=context)
        import_start_time = datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        for backend in self.browse(cr, uid, ids, context=context):
            if backend.import_products_since:
                from_date = datetime.strptime(
                        backend.import_products_since,
                        DEFAULT_SERVER_DATETIME_FORMAT)
            else:
                from_date = None
            import_batch.delay(session, 'magento.product.product',
                               backend.id, from_date=from_date)
        self.write(cr, uid, ids,
                   {'import_products_since': import_start_time})
        return True


class magento_binding(orm.AbstractModel):
    _name = 'magento.binding'
    _inherit = 'external.binding'
    _description = 'Magento Binding (abstract)'

    _columns = {
        # 'openerp_id': openerp-side id must be declared in concrete model
        'backend_id': fields.many2one(
            'magento.backend',
            'Magento Backend',
            required=True,
            ondelete='restrict'),
        # fields.char because 0 is a valid Magento ID
        'magento_id': fields.char('ID on Magento'),
    }

    # the _sql_contraints cannot be there due to this bug:
    # https://bugs.launchpad.net/openobject-server/+bug/1151703



# TODO migrate from external.shop.group
class magento_website(orm.Model):
    _name = 'magento.website'
    _inherit = 'magento.binding'

    _columns = {
        'name': fields.char('Name', required=True),
        'code': fields.char('Code'),
        'sort_order': fields.integer('Sort Order'),
        'store_ids': fields.one2many(
            'magento.store',
            'website_id',
            string="Stores",
            readonly=True),
    }

    _sql_constraints = [
        ('magento_uniq', 'unique(backend_id, magento_id)',
         'A website with the same ID on Magento already exists.'),
    ]


# TODO migrate from sale.shop (create a magento.store + associated
# sale.shop)
class magento_store(orm.Model):
    _name = 'magento.store'
    _inherit = 'magento.binding'
    _description = 'Magento Store'

    _inherits = {'sale.shop': 'openerp_id'}

    def _get_store_from_website(self, cr, uid, ids, context=None):
        store_obj = self.pool.get('magento.store')
        return store_obj.search(cr, uid,
                                [('website_id', 'in', ids)],
                                context=context)

    _columns = {
        'website_id': fields.many2one(
            'magento.website',
            'Magento Website',
            required=True,
            ondelete='cascade'),
        'openerp_id': fields.many2one(
            'sale.shop',
            string='Sale Shop',
            required=True,
            readonly=True,
            ondelete='cascade'),
        # what is the exact purpose of this field?
        'default_category_id': fields.many2one(
            'product.category',
            'Default Product Category',
            help="The category set on products when?? TODO."
            "\nOpenERP requires a main category on products for accounting."),
        'backend_id': fields.related(
            'website_id', 'backend_id',
            type='many2one',
            relation='magento.backend',
            string='Magento Backend',
            store={
                'magento.store':
                    (lambda self, cr, uid, ids, c=None:
                        ids, ['website_id'], 10),
                'magento.website':
                    (_get_store_from_website, ['backend_id'], 20),
                  },
            readonly=True),
        'storeview_ids': fields.one2many(
            'magento.storeview',
            'store_id',
            string="Storeviews",
            readonly=True),
        'send_picking_done_mail': fields.boolean(
            'Send email notification on picking done',
            help="Does the picking export/creation should send "
                 "an email notification on Magento side ?"),
        'send_invoice_paid_mail': fields.boolean(
            'Send email notification on invoice paid',
            help="Does the invoice export/creation should send "
                 "an email notification on Magento side ?"),
    }

    _sql_constraints = [
        ('magento_uniq', 'unique(backend_id, magento_id)',
         'A store with the same ID on Magento already exists.'),
    ]


class sale_shop(orm.Model):
    _inherit = 'sale.shop'

    _columns = {
        'magento_bind_ids': fields.one2many(
            'magento.store', 'openerp_id',
            string='Magento Bindings',
            readonly=True),
    }


# TODO: migrate from magerp.storeviews
class magento_storeview(orm.Model):
    _name = 'magento.storeview'
    _inherit = 'magento.binding'
    _description = "Magento Storeview"

    _columns = {
        'name': fields.char('Name', required=True),
        'code': fields.char('Code'),
        'enabled': fields.boolean('Enabled'),
        'sort_order': fields.integer('Sort Order'),
        'store_id': fields.many2one('magento.store', 'Store',
                                    ondelete='cascade'),
        'lang_id': fields.many2one('res.lang', 'Language'),
        'backend_id': fields.related(
            'store_id', 'website_id', 'backend_id',
            type='many2one',
            relation='magento.backend',
            string='Magento Backend',
            store=True,
            readonly=True),
    }

    _sql_constraints = [
        ('magento_uniq', 'unique(backend_id, magento_id)',
         'A storeview with same ID on Magento already exists.'),
    ]
