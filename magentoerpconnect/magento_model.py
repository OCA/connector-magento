# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2013 Camptocamp SA
#    Copyright 2013 Akretion
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
##############################################################################

import logging
from datetime import datetime
import magento as magentolib
from openerp.osv import fields, orm
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
import openerp.addons.connector as connector
from openerp.addons.connector.session import ConnectorSession
from openerp.addons.connector.unit.mapper import (mapping,
                                                  ImportMapper
                                                  )
from .unit.backend_adapter import GenericAdapter
from .unit.import_synchronizer import (import_batch,
                                       DirectBatchImport,
                                       )
from .partner import partner_import_batch
from .sale import sale_order_import_batch
from .backend import magento

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
        return [('1.7', '1.7')]

    _columns = {
        'version': fields.selection(
            _select_versions,
            string='Version',
            required=True),
        'location': fields.char('Location'),
        'username': fields.char('Username'),
        'password': fields.char('Password'),
        'website_ids': fields.one2many(
            'magento.website', 'backend_id',
            string='Website', readonly=True),
        'default_lang_id': fields.many2one(
                'res.lang',
                'Default Language',
                help="Choose the language which will be used for the "
                     "Default Value in Magento"),
        'default_category_id': fields.many2one(
            'product.category',
            string='Default Product Category',
            help='If a default category is selected, products imported '
                 'without a category will be linked to it.'),

        # add a field `auto_activate` -> activate a cron
        'import_products_from_date': fields.datetime('Import products from date'),
        'import_categories_from_date': fields.datetime('Import categories from date'),
        'catalog_price_tax_included': fields.boolean('Prices include tax')
    }

    def check_magento_structure(self, cr, uid, ids, context=None):
        """ Used in each data import.

        Verify if a website exists for each backend before starting the import.
        """
        for backend_id in ids:
            website_ids = self.pool['magento.website'].search(
                cr, uid, [('backend_id', '=', backend_id)], context=context)
            if not website_ids:
                self.synchronize_metadata(cr, uid, backend_id, context=context)
        return True

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

    def import_partners(self, cr, uid, ids, context=None):
        """ Import partners from all websites """
        if not hasattr(ids, '__iter__'):
            ids = [ids]
        self.check_magento_structure(cr, uid, ids, context=context)
        for backend in self.browse(cr, uid, ids, context=context):
            for website in backend.website_ids:
                website.import_partners()
        return True

    def import_sale_orders(self, cr, uid, ids, context=None):
        """ Import sale orders from all store views """
        if not hasattr(ids, '__iter__'):
            ids = [ids]
        storeview_obj = self.pool.get('magento.storeview')
        storeview_ids = storeview_obj.search(cr, uid,
                                             [('backend_id', 'in', ids)],
                                             context=context)
        storeviews = storeview_obj.browse(cr, uid, storeview_ids, context=context)
        for storeview in storeviews:
            storeview.import_sale_orders()
        return True

    def import_customer_groups(self, cr, uid, ids, context=None):
        if not hasattr(ids, '__iter__'):
            ids = [ids]
        self.check_magento_structure(cr, uid, ids, context=context)
        session = ConnectorSession(cr, uid, context=context)
        for backend_id in ids:
            import_batch.delay(session, 'magento.res.partner.category',
                               backend_id)

        return True

    def _import_from_date(self, cr, uid, ids, model, from_date_field, context=None):
        if not hasattr(ids, '__iter__'):
            ids = [ids]
        self.check_magento_structure(cr, uid, ids, context=context)
        session = ConnectorSession(cr, uid, context=context)
        import_start_time = datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        for backend in self.browse(cr, uid, ids, context=context):
            from_date = getattr(backend, from_date_field)
            if from_date:
                from_date = datetime.strptime(from_date,
                                              DEFAULT_SERVER_DATETIME_FORMAT)
            else:
                from_date = None
            import_batch.delay(session, model,
                               backend.id, filters={'from_date': from_date})
        self.write(cr, uid, ids,
                   {from_date_field: import_start_time})

    def import_product_categories(self, cr, uid, ids, context=None):
        self._import_from_date(cr, uid, ids, 'magento.product.category',
                               'import_categories_from_date', context=context)
        return True

    def import_product_product(self, cr, uid, ids, context=None):
        self._import_from_date(cr, uid, ids, 'magento.product.product',
                               'import_products_from_date', context=context)
        return True

    def _magento_backend(self, cr, uid, callback, domain=None, context=None):
        if domain is None:
            domain = []
        ids = self.search(cr, uid, domain, context=context)
        if ids:
            callback(cr, uid, ids, context=context)

    def _scheduler_import_sale_orders(self, cr, uid, domain=None, context=None):
        self._magento_backend(cr, uid, self.import_sale_orders,
                              domain=domain, context=context)

    def _scheduler_import_customer_groups(self, cr, uid, domain=None, context=None):
        self._magento_backend(cr, uid, self.import_customer_groups,
                              domain=domain, context=context)

    def _scheduler_import_partners(self, cr, uid, domain=None, context=None):
        self._magento_backend(cr, uid, self.import_partners,
                              domain=domain, context=context)

    def _scheduler_import_product_categories(self, cr, uid, domain=None, context=None):
        self._magento_backend(cr, uid, self.import_product_categories,
                              domain=domain, context=context)


# TODO migrate from external.shop.group
class magento_website(orm.Model):
    _name = 'magento.website'
    _inherit = 'magento.binding'

    _order = 'sort_order ASC'

    _columns = {
        'name': fields.char('Name', required=True, readonly=True),
        'code': fields.char('Code', readonly=True),
        'sort_order': fields.integer('Sort Order', readonly=True),
        'store_ids': fields.one2many(
            'magento.store',
            'website_id',
            string="Stores",
            readonly=True),
        'import_partners_from_date': fields.datetime('Import partners from date'),
    }

    _sql_constraints = [
        ('magento_uniq', 'unique(backend_id, magento_id)',
         'A website with the same ID on Magento already exists.'),
    ]

    def import_partners(self, cr, uid, ids, context=None):
        if not hasattr(ids, '__iter__'):
            ids = [ids]
        session = ConnectorSession(cr, uid, context=context)
        import_start_time = datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        for website in self.browse(cr, uid, ids, context=context):
            backend_id = website.backend_id.id
            if website.import_partners_from_date:
                from_date = datetime.strptime(
                        website.import_partners_from_date,
                        DEFAULT_SERVER_DATETIME_FORMAT)
            else:
                from_date = None
            partner_import_batch.delay(
                    session, 'magento.res.partner', backend_id,
                    {'magento_website_id': website.magento_id,
                     'from_date': from_date})
        self.write(cr, uid, ids,
                   {'import_partners_from_date': import_start_time})
        return True


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
            readonly=True,
            ondelete='cascade'),
        'openerp_id': fields.many2one(
            'sale.shop',
            string='Sale Shop',
            required=True,
            readonly=True,
            ondelete='cascade'),
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
                 "an email notification on Magento side?"),
        'send_invoice_paid_mail': fields.boolean(
            'Send email notification on invoice paid',
            help="Does the invoice export/creation should send "
                 "an email notification on Magento side?"),
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

    _order = 'sort_order ASC'

    _columns = {
        'name': fields.char('Name', required=True, readonly=True),
        'code': fields.char('Code', readonly=True),
        'enabled': fields.boolean('Enabled', readonly=True),
        'sort_order': fields.integer('Sort Order', readonly=True),
        'store_id': fields.many2one('magento.store', 'Store',
                                    ondelete='cascade', readonly=True),
        'lang_id': fields.many2one('res.lang', 'Language'),
        'backend_id': fields.related(
            'store_id', 'website_id', 'backend_id',
            type='many2one',
            relation='magento.backend',
            string='Magento Backend',
            store=True,
            readonly=True),
        'import_orders_from_date': fields.datetime(
            'Import sale orders from date',
            help='do not consider non-imported sale orders before this date. '
                 'Leave empty to import all sale orders'),
    }

    _sql_constraints = [
        ('magento_uniq', 'unique(backend_id, magento_id)',
         'A storeview with same ID on Magento already exists.'),
    ]

    def import_sale_orders(self, cr, uid, ids, context=None):
        session = ConnectorSession(cr, uid, context=context)
        import_start_time = datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        for storeview in self.browse(cr, uid, ids, context=context):
            backend_id = storeview.backend_id.id
            if storeview.import_orders_from_date:
                from_date = datetime.strptime(
                        storeview.import_orders_from_date,
                        DEFAULT_SERVER_DATETIME_FORMAT)
            else:
                from_date = None
            sale_order_import_batch(session, 'magento.sale.order', backend_id,
                                    {'magento_storeview_id': storeview.magento_id,
                                     'from_date': from_date,
                                     })
        self.write(cr, uid, ids, {'import_orders_from_date': import_start_time})
        return True


@magento
class WebsiteAdapter(GenericAdapter):
    _model_name = 'magento.website'
    _magento_model = 'ol_websites'


@magento
class StoreAdapter(GenericAdapter):
    _model_name = 'magento.store'
    _magento_model = 'ol_groups'


@magento
class StoreviewAdapter(GenericAdapter):
    _model_name = 'magento.storeview'
    _magento_model = 'ol_storeviews'


@magento
class MetadataBatchImport(DirectBatchImport):
    """ Import the records directly, without delaying the jobs.

    Import the Magento Websites, Stores, Storeviews

    They are imported directly because this is a rare and fast operation,
    performed from the UI.
    """
    _model_name = [
            'magento.website',
            'magento.store',
            'magento.storeview',
            ]


@magento
class WebsiteImportMapper(ImportMapper):
    _model_name = 'magento.website'

    direct = [('code', 'code'),
              ('sort_order', 'sort_order')]

    @mapping
    def name(self, record):
        name = record['name']
        if name is None:
            name = _('Undefined')
        return {'name': name}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}


@magento
class StoreImportMapper(ImportMapper):
    _model_name = 'magento.store'

    direct = [('name', 'name')]

    @mapping
    def website_id(self, record):
        binder = self.get_binder_for_model('magento.website')
        openerp_id = binder.to_openerp(record['website_id'])
        return {'website_id': openerp_id}

    @mapping
    def warehouse_id(self, record):
        """ set the warehouse_id of the sale.shop (via _inherits)
        because this is a mandatory field """
        sess = self.session
        cr, uid, pool, ctx = sess.cr, sess.uid, sess.pool, sess.context
        company_obj = pool['res.company']
        warehouse_obj = pool['stock.warehouse']
        company_id = company_obj._company_default_get(cr, uid,
                                                      'sale.shop',
                                                      context=ctx)
        warehouse_ids = warehouse_obj.search(cr, uid,
                                             [('company_id', '=', company_id)],
                                             context=ctx)
        return {'warehouse_id': warehouse_ids[0]}


@magento
class StoreviewImportMapper(ImportMapper):
    _model_name = 'magento.storeview'

    direct = [
        ('name', 'name'),
        ('code', 'code'),
        ('is_active', 'enabled'),
        ('sort_order', 'sort_order'),
    ]

    @mapping
    def store_id(self, record):
        binder = self.get_binder_for_model('magento.store')
        openerp_id = binder.to_openerp(record['group_id'])
        return {'store_id': openerp_id}
