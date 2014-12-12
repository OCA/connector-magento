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
from datetime import datetime, timedelta
from openerp.osv import fields, orm
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.translate import _
from openerp.addons.connector.session import ConnectorSession
from openerp.addons.connector.connector import ConnectorUnit
from openerp.addons.connector.unit.mapper import (mapping,
                                                  only_create,
                                                  ImportMapper
                                                  )
from .unit.backend_adapter import GenericAdapter
from .unit.import_synchronizer import (import_batch,
                                       DirectBatchImport,
                                       MagentoImportSynchronizer,
                                       AddCheckpoint,
                                       )
from .partner import partner_import_batch
from .sale import sale_order_import_batch
from .backend import magento
from .connector import add_checkpoint

_logger = logging.getLogger(__name__)

IMPORT_DELTA_BUFFER = 30  # seconds


class magento_backend(orm.Model):
    _name = 'magento.backend'
    _description = 'Magento Backend'
    _inherit = 'connector.backend'

    _backend_type = 'magento'

    def select_versions(self, cr, uid, context=None):
        """ Available versions in the backend.

        Can be inherited to add custom versions.  Using this method
        to add a version from an ``_inherit`` does not constrain
        to redefine the ``version`` field in the ``_inherit`` model.
        """
        return [('1.7', '1.7')]

    def _select_versions(self, cr, uid, context=None):
        """ Available versions in the backend.

        If you want to add a version, do not override this
        method, but ``select_version``.
        """
        return self.select_versions(cr, uid, context=context)

    def _get_stock_field_id(self, cr, uid, context=None):
        field_ids = self.pool.get('ir.model.fields').search(
            cr, uid,
            [('model', '=', 'product.product'),
             ('name', '=', 'virtual_available')],
            context=context)
        return field_ids[0]

    _columns = {
        'version': fields.selection(
            _select_versions,
            string='Version',
            required=True),
        'location': fields.char(
            'Location',
            required=True,
            help="Url to magento application"),
        'admin_location': fields.char('Admin Location'),
        'use_custom_api_path': fields.boolean(
            'Custom Api Path',
            help="The default API path is '/index.php/api/xmlrpc'. "
                 "Check this box if you use a custom API path, in that case, "
                 "the location has to be completed with the custom API path "),
        'username': fields.char(
            'Username',
            help="Webservice user"),
        'password': fields.char(
            'Password',
            help="Webservice password"),
        'use_auth_basic': fields.boolean(
            'Use HTTP Auth Basic',
            help="Use a Basic Access Authentication for the API. "
                 "The Magento server could be configured to restrict access "
                 "using a HTTP authentication based on a username and "
                 "a password."),
        'auth_basic_username': fields.char(
            'Basic Auth. Username',
            help="Basic access authentication web server side username"),
        'auth_basic_password': fields.char(
            'Basic Auth. Password',
            help="Basic access authentication web server side password"),
        'sale_prefix': fields.char(
            'Sale Prefix',
            help="A prefix put before the name of imported sales orders.\n"
                 "For instance, if the prefix is 'mag-', the sales "
                 "order 100000692 in Magento, will be named 'mag-100000692' "
                 "in OpenERP."),
        'warehouse_id': fields.many2one('stock.warehouse',
                                        'Warehouse',
                                        required=True,
                                        help='Warehouse used to compute the '
                                             'stock quantities.'),
        'website_ids': fields.one2many(
            'magento.website', 'backend_id',
            string='Website', readonly=True),
        'default_lang_id': fields.many2one(
            'res.lang',
            'Default Language',
            help="If a default language is selected, the records "
                 "will be imported in the translation of this language.\n"
                 "Note that a similar configuration exists "
                 "for each storeview."),
        'default_category_id': fields.many2one(
            'product.category',
            string='Default Product Category',
            help='If a default category is selected, products imported '
                 'without a category will be linked to it.'),

        # add a field `auto_activate` -> activate a cron
        'import_products_from_date': fields.datetime(
            'Import products from date'),
        'import_categories_from_date': fields.datetime(
            'Import categories from date'),
        'product_stock_field_id': fields.many2one(
            'ir.model.fields',
            string='Stock Field',
            domain="[('model', 'in', ['product.product', 'product.template']),"
                   " ('ttype', '=', 'float')]",
            help="Choose the field of the product which will be used for "
                 "stock inventory updates.\nIf empty, Quantity Available "
                 "is used."),
        'product_binding_ids': fields.one2many('magento.product.product',
                                               'backend_id',
                                               string='Magento Products',
                                               readonly=True),
    }

    _defaults = {
        'product_stock_field_id': _get_stock_field_id,
        'use_custom_api_path': False,
        'use_auth_basic': False,
    }

    _sql_constraints = [
        ('sale_prefix_uniq', 'unique(sale_prefix)',
         "A backend with the same sale prefix already exists")
    ]

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
        storeviews = storeview_obj.browse(cr, uid, storeview_ids,
                                          context=context)
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

    def _import_from_date(self, cr, uid, ids, model, from_date_field,
                          context=None):
        if not hasattr(ids, '__iter__'):
            ids = [ids]
        self.check_magento_structure(cr, uid, ids, context=context)
        session = ConnectorSession(cr, uid, context=context)
        import_start_time = datetime.now()
        for backend in self.browse(cr, uid, ids, context=context):
            from_date = getattr(backend, from_date_field)
            if from_date:
                from_date = datetime.strptime(from_date,
                                              DEFAULT_SERVER_DATETIME_FORMAT)
            else:
                from_date = None
            import_batch.delay(session, model,
                               backend.id,
                               filters={'from_date': from_date,
                                        'to_date': import_start_time})
        # Records from Magento are imported based on their `created_at`
        # date.  This date is set on Magento at the beginning of a
        # transaction, so if the import is run between the beginning and
        # the end of a transaction, the import of a record may be
        # missed.  That's why we add a small buffer back in time where
        # the eventually missed records will be retrieved.  This also
        # means that we'll have jobs that import twice the same records,
        # but this is not a big deal because they will be skipped when
        # the last `sync_date` is the same.
        next_time = import_start_time - timedelta(seconds=IMPORT_DELTA_BUFFER)
        next_time = next_time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        self.write(cr, uid, ids, {from_date_field: next_time}, context=context)

    def import_product_categories(self, cr, uid, ids, context=None):
        self._import_from_date(cr, uid, ids, 'magento.product.category',
                               'import_categories_from_date', context=context)
        return True

    def import_product_product(self, cr, uid, ids, context=None):
        self._import_from_date(cr, uid, ids, 'magento.product.product',
                               'import_products_from_date', context=context)
        return True

    def _domain_for_update_product_stock_qty(self, cr, uid, ids, context=None):
        return [
            ('backend_id', 'in', ids),
            ('type', '!=', 'service'),
            ('no_stock_sync', '=', False), ]

    def update_product_stock_qty(self, cr, uid, ids, context=None):
        if not hasattr(ids, '__iter__'):
            ids = [ids]
        mag_product_obj = self.pool.get('magento.product.product')
        domain = self._domain_for_update_product_stock_qty(cr, uid, ids,
                                                           context=context)
        product_ids = mag_product_obj.search(cr, uid, domain, context=context)
        mag_product_obj.recompute_magento_qty(cr, uid, product_ids,
                                              context=context)
        return True

    def _magento_backend(self, cr, uid, callback, domain=None, context=None):
        if domain is None:
            domain = []
        ids = self.search(cr, uid, domain, context=context)
        if ids:
            callback(cr, uid, ids, context=context)

    def _scheduler_import_sale_orders(self, cr, uid, domain=None,
                                      context=None):
        self._magento_backend(cr, uid, self.import_sale_orders,
                              domain=domain, context=context)

    def _scheduler_import_customer_groups(self, cr, uid, domain=None,
                                          context=None):
        self._magento_backend(cr, uid, self.import_customer_groups,
                              domain=domain, context=context)

    def _scheduler_import_partners(self, cr, uid, domain=None, context=None):
        self._magento_backend(cr, uid, self.import_partners,
                              domain=domain, context=context)

    def _scheduler_import_product_categories(self, cr, uid, domain=None,
                                             context=None):
        self._magento_backend(cr, uid, self.import_product_categories,
                              domain=domain, context=context)

    def _scheduler_import_product_product(self, cr, uid, domain=None,
                                          context=None):
        self._magento_backend(cr, uid, self.import_product_product,
                              domain=domain, context=context)

    def _scheduler_update_product_stock_qty(self, cr, uid,
                                            domain=None, context=None):
        self._magento_backend(cr, uid, self.update_product_stock_qty,
                              domain=domain, context=context)

    def output_recorder(self, cr, uid, ids, context=None):
        """ Utility method to output a file containing all the recorded
        requests / responses with Magento.  Used to generate test data.
        Should be called with ``erppeek`` for instance.
        """
        from .unit.backend_adapter import output_recorder
        import os
        import tempfile
        fmt = '%Y-%m-%d-%H-%M-%S'
        timestamp = datetime.now().strftime(fmt)
        filename = 'output_%s_%s' % (cr.dbname, timestamp)
        path = os.path.join(tempfile.gettempdir(), filename)
        output_recorder(path)
        return path


# TODO migrate from external.shop.group
class magento_website(orm.Model):
    _name = 'magento.website'
    _inherit = 'magento.binding'
    _description = 'Magento Website'

    _order = 'sort_order ASC, id ASC'

    _columns = {
        'name': fields.char('Name', required=True, readonly=True),
        'code': fields.char('Code', readonly=True),
        'sort_order': fields.integer('Sort Order', readonly=True),
        'store_ids': fields.one2many(
            'magento.store',
            'website_id',
            string="Stores",
            readonly=True),
        'import_partners_from_date': fields.datetime(
            'Import partners from date'),
        'product_binding_ids': fields.many2many('magento.product.product',
                                                string='Magento Products',
                                                readonly=True),
    }

    _sql_constraints = [
        ('magento_uniq', 'unique(backend_id, magento_id)',
         'A website with the same ID on Magento already exists.'),
    ]

    def import_partners(self, cr, uid, ids, context=None):
        if not hasattr(ids, '__iter__'):
            ids = [ids]
        session = ConnectorSession(cr, uid, context=context)
        import_start_time = datetime.now()
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
                 'from_date': from_date,
                 'to_date': import_start_time})
        # Records from Magento are imported based on their `created_at`
        # date.  This date is set on Magento at the beginning of a
        # transaction, so if the import is run between the beginning and
        # the end of a transaction, the import of a record may be
        # missed.  That's why we add a small buffer back in time where
        # the eventually missed records will be retrieved.  This also
        # means that we'll have jobs that import twice the same records,
        # but this is not a big deal because they will be skipped when
        # the last `sync_date` is the same.
        next_time = import_start_time - timedelta(seconds=IMPORT_DELTA_BUFFER)
        next_time = next_time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        self.write(cr, uid, ids, {'import_partners_from_date': next_time},
                   context=context)
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
                'magento.store': (lambda self, cr, uid, ids, c=None: ids,
                                  ['website_id'], 10),
                'magento.website': (_get_store_from_website,
                                    ['backend_id'], 20),
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
            'Send email notification on invoice validated/paid',
            help="Does the invoice export/creation should send "
                 "an email notification on Magento side?"),
        'create_invoice_on': fields.selection(
            [('open', 'Validate'),
             ('paid', 'Paid')],
            'Create invoice on action',
            required=True,
            help="Should the invoice be created in Magento "
                 "when it is validated or when it is paid in OpenERP?\n"
                 "This only takes effect if the sales order's related "
                 "payment method is not giving an option for this by "
                 "itself. (See Payment Methods)"),
    }

    _defaults = {
        'create_invoice_on': 'paid',
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

    def copy_data(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default['magento_bind_ids'] = False
        return super(sale_shop, self).copy_data(cr, uid, id,
                                                default=default,
                                                context=context)


# TODO: migrate from magerp.storeviews
class magento_storeview(orm.Model):
    _name = 'magento.storeview'
    _inherit = 'magento.binding'
    _description = "Magento Storeview"

    _order = 'sort_order ASC, id ASC'

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
        'no_sales_order_sync': fields.boolean(
            'No Sales Order Synchronization',
            help='Check if the storeview is active in Magento '
                 'but its sales orders should not be imported.'),
        'catalog_price_tax_included': fields.boolean('Prices include tax'),
    }

    _defaults = {
        'no_sales_order_sync': False,
    }

    _sql_constraints = [
        ('magento_uniq', 'unique(backend_id, magento_id)',
         'A storeview with same ID on Magento already exists.'),
    ]

    def import_sale_orders(self, cr, uid, ids, context=None):
        session = ConnectorSession(cr, uid, context=context)
        import_start_time = datetime.now()
        for storeview in self.browse(cr, uid, ids, context=context):
            if storeview.no_sales_order_sync:
                _logger.debug("The storeview '%s' is active in Magento "
                              "but its sales orders should not be imported." %
                              storeview.name)
                continue
            backend_id = storeview.backend_id.id
            if storeview.import_orders_from_date:
                from_date = datetime.strptime(
                    storeview.import_orders_from_date,
                    DEFAULT_SERVER_DATETIME_FORMAT)
            else:
                from_date = None
            sale_order_import_batch.delay(
                session,
                'magento.sale.order',
                backend_id,
                {'magento_storeview_id': storeview.magento_id,
                 'from_date': from_date,
                 'to_date': import_start_time},
                priority=1)  # executed as soon as possible
        # Records from Magento are imported based on their `created_at`
        # date.  This date is set on Magento at the beginning of a
        # transaction, so if the import is run between the beginning and
        # the end of a transaction, the import of a record may be
        # missed.  That's why we add a small buffer back in time where
        # the eventually missed records will be retrieved.  This also
        # means that we'll have jobs that import twice the same records,
        # but this is not a big deal because the sales orders will be
        # imported the first time and the jobs will be skipped on the
        # subsequent imports
        next_time = import_start_time - timedelta(seconds=IMPORT_DELTA_BUFFER)
        next_time = next_time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        self.write(cr, uid, ids, {'import_orders_from_date': next_time},
                   context=context)
        return True


@magento
class WebsiteAdapter(GenericAdapter):
    _model_name = 'magento.website'
    _magento_model = 'ol_websites'
    _admin_path = 'system_store/editWebsite/website_id/{id}'


@magento
class StoreAdapter(GenericAdapter):
    _model_name = 'magento.store'
    _magento_model = 'ol_groups'
    _admin_path = 'system_store/editGroup/group_id/{id}'


@magento
class StoreviewAdapter(GenericAdapter):
    _model_name = 'magento.storeview'
    _magento_model = 'ol_storeviews'
    _admin_path = 'system_store/editStore/store_id/{id}'


@magento
class MetadataBatchImport(DirectBatchImport):
    """ Import the records directly, without delaying the jobs.

    Import the Magento Websites, Stores, Storeviews

    They are imported directly because this is a rare and fast operation,
    and we don't really bother if it blocks the UI during this time.
    (that's also a mean to rapidly check the connectivity with Magento).
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
        binding_id = binder.to_openerp(record['website_id'])
        return {'website_id': binding_id}

    @mapping
    @only_create
    def warehouse_id(self, record):
        return {'warehouse_id': self.backend_record.warehouse_id.id}


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
        binding_id = binder.to_openerp(record['group_id'])
        return {'store_id': binding_id}


@magento
class StoreImport(MagentoImportSynchronizer):
    """ Import one Magento Store (create a sale.shop via _inherits) """
    _model_name = ['magento.store',
                   ]

    def _create(self, data):
        openerp_binding_id = super(StoreImport, self)._create(data)
        checkpoint = self.get_connector_unit_for_model(AddCheckpoint)
        checkpoint.run(openerp_binding_id)
        return openerp_binding_id


@magento
class StoreviewImport(MagentoImportSynchronizer):
    """ Import one Magento Storeview """
    _model_name = ['magento.storeview',
                   ]

    def _create(self, data):
        openerp_binding_id = super(StoreviewImport, self)._create(data)
        checkpoint = self.get_connector_unit_for_model(StoreViewAddCheckpoint)
        checkpoint.run(openerp_binding_id)
        return openerp_binding_id


@magento
class StoreViewAddCheckpoint(ConnectorUnit):
    """ Add a connector.checkpoint on the magento.storeview
    record """
    _model_name = ['magento.storeview',
                   ]

    def run(self, openerp_binding_id):
        add_checkpoint(self.session,
                       self.model._name,
                       openerp_binding_id,
                       self.backend_record.id)
