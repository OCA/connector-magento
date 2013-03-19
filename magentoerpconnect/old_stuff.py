# -*- coding: utf-8 -*-
import logging

from openerp.osv import fields
from openerp.osv.osv import except_osv
from openerp import pooler
from openerp import tools
from openerp.tools.translate import _

from .magerp_osv import MagerpModel, Connection
from openerp.addons.connector.decorator import only_for_referential
from openerp.addons.connector.external_osv import ExternalSession

import openerp.addons.connector as connector


_logger = logging.getLogger(__name__)



DEBUG = True
TIMEOUT = 2


# Don't go below this point unless you're not afraid of spiderwebs ################

# TODO: move all the stuff related to Magento in magento.backend
class external_referential(MagerpModel):
    #This class stores instances of magento to which the ERP will
    #connect, so you can connect OpenERP to multiple Magento
    #installations (eg different Magento databases)
    _inherit = "external.referential"

    SYNC_PRODUCT_FILTERS = {'status': {'=': 1}}
    SYNC_PARTNER_FILTERS = {}
    SYNC_PARTNER_STEP = 500

    def _is_magento_referential(self, cr, uid, ids, field_name, arg, context=None):
        """If at least one shop is magento, we consider that the external
        referential is a magento referential
        """
        res = {}
        for referential in self.browse(cr, uid, ids, context):
            if referential.type_id.name == 'magento':
                res[referential.id] = True
            else:
                res[referential.id] = False
        return res

    _columns = {
        'attribute_sets':fields.one2many('magerp.product_attribute_set', 'referential_id', 'Attribute Sets'),
        'default_pro_cat':fields.many2one('product.category','Default Product Category', help="Products imported from magento may have many categories.\nOpenERP requires a specific category for a product to facilitate invoicing etc."),
        'default_lang_id':fields.many2one('res.lang', 'Default Language', help="Choose the language which will be used for the Default Value in Magento"),
        'active': fields.boolean('Active'),
        'magento_referential': fields.function(_is_magento_referential, type="boolean", method=True, string="Magento Referential"),
        'last_imported_product_id': fields.integer('Last Imported Product Id', help="Product are imported one by one. This is the magento id of the last product imported. If you clear it all product will be imported"),
        'last_imported_partner_id': fields.integer('Last Imported Partner Id', help="Partners are imported one by one. This is the magento id of the last partner imported. If you clear it all partners will be imported"),
        'import_all_attributs': fields.boolean('Import all attributs', help="If the option is uncheck only the attributs that doesn't exist in OpenERP will be imported"),
        'import_image_with_product': fields.boolean('With image', help="If the option is check the product's image and the product will be imported at the same time and so the step '7-import images' is not needed"),
        'import_links_with_product': fields.boolean('With links', help="If the option is check the product's links (Up-Sell, Cross-Sell, Related) and the product will be imported at the same time and so the step '8-import links' is not needed"),
    }

    _defaults = {
        'active': lambda *a: 1,
    }

    @only_for_referential('magento')
    def external_connection(self, cr, uid, id, debug=False, logger=False, context=None):
        if isinstance(id, list):
            id=id[0]
        referential = self.browse(cr, uid, id, context=context)
        attr_conn = Connection(referential.location, referential.apiusername, referential.apipass, debug, logger)
        return attr_conn.connect() and attr_conn or False

    @only_for_referential('magento')
    def import_referentials(self, cr, uid, ids, context=None):
        self.import_resources(cr, uid, ids, 'external.shop.group', method='search_read_no_loop', context=context)
        self.import_resources(cr, uid, ids, 'sale.shop', method='search_read_no_loop', context=context)
        self.import_resources(cr, uid, ids, 'magerp.storeviews', method='search_read_no_loop', context=context)
        return True

    @only_for_referential('magento')
    def import_product_categories(self, cr, uid, ids, context=None):
        self.import_resources(cr, uid, ids, 'product.category', method='search_then_read_no_loop', context=context)
        return True


    #This function will be refactored latter, need to improve Magento API before
    def sync_attribs(self, cr, uid, ids, context=None):
        attr_obj = self.pool.get('magerp.product_attributes')
        attr_set_obj = self.pool.get('magerp.product_attribute_set')
        for referential in self.browse(cr, uid, ids, context=context):
            external_session = ExternalSession(referential, referential)
            attr_conn = external_session.connection
            attrib_set_ids = attr_set_obj.search(cr, uid, [('referential_id', '=', referential.id)])
            attrib_sets = attr_set_obj.read(cr, uid, attrib_set_ids, ['magento_id'])
            #Get all attribute set ids to get all attributes in one go
            all_attr_set_ids = attr_set_obj.get_all_extid_from_referential(cr, uid, referential.id, context=context)
            #Call magento for all attributes
            if referential.import_all_attributs:
                attributes_imported=[]
            else:
                attributes_imported = attr_obj.get_all_extid_from_referential(cr, uid, referential.id, context=context)
            import_cr = pooler.get_db(cr.dbname).cursor()

            mapping = {'magerp.product_attributes' : attr_obj._get_mapping(cr, uid, referential.id, context=context)}
            try:
                for attr_set_id in all_attr_set_ids:
                    mage_inp = attr_conn.call('ol_catalog_product_attribute.list', [attr_set_id])             #Get the tree
                    attribut_to_import = []
                    for attribut in mage_inp:
                        ext_id = attribut['attribute_id']
                        if not ext_id in attributes_imported:
                            attributes_imported.append(ext_id)
                            attr_obj._record_one_external_resource(import_cr, uid, external_session, attribut,
                                                            defaults={'referential_id':referential.id},
                                                            mapping=mapping,
                                                            context=context,
                                                        )
                            import_cr.commit()
                    _logger.info("All attributs for the attributs set id %s was succesfully imported", attr_set_id)
                #Relate attribute sets & attributes
                mage_inp = {}
                #Pass in {attribute_set_id:{attributes},attribute_set_id2:{attributes}}
                #print "Attribute sets are:", attrib_sets
                #TODO find a solution in order to import the relation in a incremental way (maybe splitting this function in two)
                for each in attrib_sets:
                    mage_inp[each['magento_id']] = attr_conn.call('ol_catalog_product_attribute.relations', [each['magento_id']])
                if mage_inp:
                    attr_set_obj.relate(import_cr, uid, mage_inp, referential.id, DEBUG)
                import_cr.commit()
            finally:
                import_cr.close()
        return True

    def sync_attrib_sets(self, cr, uid, ids, context=None):
        return self.import_resources(cr, uid, ids, 'magerp.product_attribute_set', method='search_read_no_loop', context=context)

    def sync_attrib_groups(self, cr, uid, ids, context=None):
        return self.import_resources(cr, uid, ids, 'magerp.product_attribute_groups', method='search_read_no_loop', context=context)

    @only_for_referential('magento')
    def import_customer_groups(self, cr, uid, ids, context=None):
        return self.import_resources(cr, uid, ids, 'res.partner.category', method='search_read_no_loop', context=context)

    def sync_customer_addresses(self, cr, uid, ids, context=None):
        for referential_id in ids:
            attr_conn = self.external_connection(cr, uid, referential_id, DEBUG, context=context)
            filter = []
            #self.pool.get('res.partner').mage_import(cr, uid, filter, attr_conn, referential_id, DEBUG)
            #TODO fix by retrieving customer list first
            self.pool.get('res.partner.address').mage_import_base(cr, uid, attr_conn, referential_id, {}, {'ids_or_filter':filter})
        return True

    def _sync_product_storeview(self, cr, uid, external_session, referential_id, ext_product_id, storeview, mapping=None, context=None):
        if context is None: context = {}
        #we really need to clean all magento call and give the posibility to force everythere to use the id as identifier
        product_info = external_session.connection.call('catalog_product.info', [ext_product_id, storeview.code, False, 'id'])
        ctx = context.copy()
        ctx.update({'magento_sku': product_info['sku']})
        defaults={'magento_exportable': True}
        return self.pool.get('product.product')._record_one_external_resource(cr, uid, external_session, product_info,
                                                            defaults=defaults,
                                                            mapping=mapping,
                                                            context=ctx,
                                                        )
    # This function will be refactored later, maybe it will be better
    # to improve the magento API before
    def sync_products(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        prod_obj = self.pool.get('product.product')
#        context.update({'dont_raise_error': True})
        for referential in self.browse(cr, uid, ids, context):
            external_session = ExternalSession(referential, referential)
            attr_conn = external_session.connection
            mapping = {'product.product' : prod_obj._get_mapping(cr, uid,
                                                                 referential.id,
                                                                 context=context)
                       }
            filter = []
            if referential.last_imported_product_id:
                filters = {'product_id': {'gt': referential.last_imported_product_id}}
                filters.update(self.SYNC_PRODUCT_FILTERS)
                filter = [filters]
            #TODO call method should be not harcoded. Need refactoring
            ext_product_ids = attr_conn.call('ol_catalog_product.search', filter)
            storeview_obj = self.pool.get('magerp.storeviews')

            #get all instance storeviews
            storeview_ids = []
            for website in referential.shop_group_ids:
                for shop in website.shop_ids:
                    for storeview in shop.storeview_ids:
                        storeview_ids += [storeview.id]

            lang_2_storeview={}
            for storeview in storeview_obj.browse(cr, uid, storeview_ids, context):
                #get lang of the storeview
                lang_id = storeview.lang_id
                if lang_id:
                    lang = lang_id.code
                else:
                    except_osv(_('Warning!'), _('The storeviews have no language defined')) #TODO needed?
                    lang = referential.default_lang_id.code
                if not lang_2_storeview.get(lang, False):
                    lang_2_storeview[lang] = storeview

            if referential.import_links_with_product:
                link_types = self.get_magento_product_link_types(cr, uid, referential.id, attr_conn, context=context)

            import_cr = pooler.get_db(cr.dbname).cursor()
            try:
                for ext_product_id in ext_product_ids:
                    for lang, storeview in lang_2_storeview.iteritems():
                        ctx = context.copy()
                        ctx.update({'lang': lang})
                        res = self._sync_product_storeview(import_cr, uid, external_session, referential.id, ext_product_id, storeview, mapping=mapping, context=ctx)
                    product_id = (res.get('create_id') or res.get('write_id'))
                    if referential.import_image_with_product:
                        prod_obj.import_product_image(import_cr, uid, product_id, referential.id, attr_conn, ext_id=ext_product_id, context=context)
                    if referential.import_links_with_product:
                        prod_obj.mag_import_product_links_types(import_cr, uid, product_id, link_types,  external_session, context=context)
                    self.write(import_cr, uid, referential.id, {'last_imported_product_id': int(ext_product_id)}, context=context)
                    import_cr.commit()
            finally:
                import_cr.close()
        return True

    def get_magento_product_link_types(self, cr, uid, ids, conn=None, context=None):
        if not conn:
            conn = self.external_connection(cr, uid, ids, DEBUG, context=context)
        return conn.call('catalog_product_link.types')

    #TODO refactore me base on connector
    def sync_images(self, cr, uid, ids, context=None):
        product_obj = self.pool.get('product.product')
        image_obj = self.pool.get('product.images')
        import_cr = pooler.get_db(cr.dbname).cursor()
        try:
            for referential in self.browse(cr, uid, ids, context=context):
                external_session = ExternalSession(referential, referential)
                conn = external_session.connection
                product_ids = product_obj.get_all_oeid_from_referential(cr, uid, referential.id, context=context)
                for product_id in product_ids:
                    product_obj.import_product_image(import_cr, uid, product_id, referential.id, conn, context=context)
                    import_cr.commit()
        finally:
            import_cr.close()
        return True

    #TODO refactore me base on connector
    def sync_product_links(self, cr, uid, ids, context=None):
        if context is None: context = {}
        for referential in self.browse(cr, uid, ids, context):
            external_session = ExternalSession(referential, referential)
            conn = external_session.connection
            exportable_product_ids= []
            for shop_group in referential.shop_group_ids:
                for shop in shop_group.shop_ids:
                    exportable_product_ids.extend([product.id for product in shop.exportable_product_ids])
            exportable_product_ids = list(set(exportable_product_ids))
            self.pool.get('product.product').mag_import_product_links(cr, uid, exportable_product_ids, external_session, context=context)
        return True

    def export_products(self, cr, uid, ids, context=None):
        if context is None: context = {}
        shop_ids = self.pool.get('sale.shop').search(cr, uid, [])
        for referential_id in ids:
            for shop in self.pool.get('sale.shop').browse(cr, uid, shop_ids, context):
                context['conn_obj'] = self.external_connection(cr, uid, referential_id, context=context)
                #shop.export_catalog
                tools.debug((cr, uid, shop, context,))
                shop.export_products(cr, uid, shop, context)
        return True

    #TODO refactor me
    def sync_partner(self, cr, uid, ids, context=None):
        def next_partners(connection, start, step):
            filters = {'customer_id': {'in': range(start, start + step)}}
            filters.update(self.SYNC_PARTNER_FILTERS)
            filter = [filters]
            return attr_conn.call('ol_customer.search', filter)

        for referential in self.browse(cr, uid, ids, context):
            attr_conn = referential.external_connection(DEBUG)
            last_imported_id = 0
            if referential.last_imported_partner_id:
                last_imported_id = referential.last_imported_partner_id

            ext_customer_ids = next_partners(attr_conn, last_imported_id + 1, self.SYNC_PARTNER_STEP)
            import_cr = pooler.get_db(cr.dbname).cursor()
            try:
                while ext_customer_ids:
                    for ext_customer_id in ext_customer_ids:
                        customer_info = attr_conn.call('customer.info', [ext_customer_id])
                        customer_address_info = attr_conn.call('customer_address.list', [ext_customer_id])

                        address_info = False
                        if customer_address_info:
                            address_info = customer_address_info[0]
                            address_info['customer_id'] = ext_customer_id
                            address_info['email'] = customer_info['email']
                        external_session = ExternalSession(referential, referential)
                        self.pool.get('res.partner')._record_one_external_resource(import_cr, uid, external_session, customer_info, context=context)
                        if address_info:
                            self.pool.get('res.partner.address')._record_one_external_resource(import_cr, uid, external_session, address_info, context=context)
                        last_imported_id = int(ext_customer_id)
                        self.write(import_cr, uid, referential.id, {'last_imported_partner_id': last_imported_id}, context=context)
                        import_cr.commit()
                    ext_customer_ids = next_partners(attr_conn, last_imported_id + 1, self.SYNC_PARTNER_STEP)
            finally:
                import_cr.close()
        return True

    def sync_newsletter(self, cr, uid, ids, context=None):
        #update first all customer
        self.sync_partner(cr, uid, ids, context)

        partner_obj = self.pool.get('res.partner')

        for referential_id in ids:
            attr_conn = self.external_connection(cr, uid, referential_id, DEBUG, context=context)
            filter = []
            list_subscribers = attr_conn.call('ol_customer_subscriber.list')
            result = []
            for each in list_subscribers:
                each_subscribers_info = attr_conn.call('ol_customer_subscriber.info', [each])

                # search this customer. If exist, update your newsletter subscription
                partner_ids = partner_obj.search(cr, uid, [('emailid', '=', each_subscribers_info[0]['subscriber_email'])])
                if partner_ids:
                    #unsubscriber magento value: 3
                    if int(each_subscribers_info[0]['subscriber_status']) == 1:
                        subscriber_status = 1
                    else:
                        subscriber_status = 0
                    partner_obj.write(cr, uid, partner_ids[0], {'mag_newsletter': subscriber_status})
        return True

    def sync_newsletter_unsubscriber(self, cr, uid, ids, context=None):
        partner_obj = self.pool.get('res.partner')

        for referential_id in ids:
            attr_conn = self.external_connection(cr, uid, referential_id, DEBUG, context=context)
            partner_ids  = partner_obj.search(cr, uid, [('mag_newsletter', '!=', 1), ('emailid', '!=', '')])

            for partner in partner_obj.browse(cr, uid, partner_ids):
                if partner.emailid:
                    attr_conn.call('ol_customer_subscriber.delete', [partner.emailid])

        return True

    # Schedules functions ============ #
    def run_import_newsletter_scheduler(self, cr, uid, context=None):
        if context is None:
            context = {}

        referential_ids  = self.search(cr, uid, [('active', '=', 1)])

        if referential_ids:
            self.sync_newsletter(cr, uid, referential_ids, context)
        if DEBUG:
            print "run_import_newsletter_scheduler: %s" % referential_ids

    def run_import_newsletter_unsubscriber_scheduler(self, cr, uid, context=None):
        if context is None:
            context = {}

        referential_ids  = self.search(cr, uid, [('active', '=', 1)])

        if referential_ids:
            self.sync_newsletter_unsubscriber(cr, uid, referential_ids, context)
        if DEBUG:
            print "run_import_newsletter_unsubscriber_scheduler: %s" % referential_ids


# TODO: remove
class external_shop_group(MagerpModel):
    _inherit = "external.shop.group"
    #Return format of API:{'code': 'base', 'name': 'Main', 'website_id': '1', 'is_default': '1', 'sort_order': '0', 'default_group_id': '1'}
    # default_group_id is the default shop of the external_shop_group (external_shop_group = website)

    def _get_default_shop_id(self, cr, uid, ids, prop, unknow_none, context=None):
        res = {}
        for shop_group in self.browse(cr, uid, ids, context):
            if shop_group.default_shop_integer_id:
                rid = self.pool.get('sale.shop').extid_to_existing_oeid(cr, uid, shop_group.default_shop_integer_id, shop_group.referential_id.id)
                res[shop_group.id] = rid
            else:
                res[shop_group.id] = False
        return res

    _columns = {
        'code':fields.char('Code', size=100),
        'is_default':fields.boolean('Is Default?'),
        'sort_order':fields.integer('Sort Order'),
        'default_shop_integer_id':fields.integer('Default Store'), #This field can't be a many2one because shop_group field will be mapped before creating Shop (Shop = Store, shop_group = website)
        'default_shop_id':fields.function(_get_default_shop_id, type="many2one", relation="sale.shop", method=True, string="Default Store"),
        'referential_type' : fields.related('referential_id', 'type_id', type='many2one', relation='external.referential.type', string='External Referential Type'),
        }


# TODO: remove
class magerp_storeviews(MagerpModel):
    _name = "magerp.storeviews"
    _description = "The magento store views information"

    _columns = {
        'name':fields.char('Store View Name', size=100),
        'code':fields.char('Code', size=100),
        'website_id':fields.many2one('external.shop.group', 'Website', select=True, ondelete='cascade'),
        'is_active':fields.boolean('Default ?'),
        'sort_order':fields.integer('Sort Order'),
        'shop_id':fields.many2one('sale.shop', 'Shop', select=True, ondelete='cascade'),
        'lang_id':fields.many2one('res.lang', 'Language'),
    }


# transfered from sale.py ###############################

if False:


    
    class sale_shop(Model):
        _inherit = "sale.shop"

        @only_for_referential('magento')
        def init_context_before_exporting_resource(self, cr, uid, external_session, object_id, resource_name, context=None):
            context = super(sale_shop, self).init_context_before_exporting_resource(cr, uid, external_session, object_id, resource_name, context=context)
            shop = self.browse(cr, uid, object_id, context=context)
            context['main_lang'] = shop.referential_id.default_lang_id.code
            context['lang_to_export'] = [shop.referential_id.default_lang_id.code]
            context['storeview_to_lang'] = {}
            for storeview in shop.storeview_ids:
                if storeview.lang_id and storeview.lang_id.code != shop.referential_id.default_lang_id.code:
                    context['storeview_to_lang'][storeview.code] = storeview.lang_id.code
                    if not storeview.lang_id.code in context['lang_to_export']:
                        context['lang_to_export'].append(storeview.lang_id.code)
            return context

        def _get_exportable_product_ids(self, cr, uid, ids, name, args, context=None):
            res = super(sale_shop, self)._get_exportable_product_ids(cr, uid, ids, name, args, context=None)
            for shop_id in res:
                website_id =  self.read(cr, uid, shop_id, ['shop_group_id'])
                if website_id.get('shop_group_id', False):
                    res[shop_id] = self.pool.get('product.product').search(cr, uid,
                                                                           [('magento_exportable', '=', True),
                                                                            ('id', 'in', res[shop_id]),
                                                                            "|", ('websites_ids', 'in', [website_id['shop_group_id'][0]]),
                                                                                 ('websites_ids', '=', False)])
                else:
                    res[shop_id] = []
            return res

        def _get_default_storeview_id(self, cr, uid, ids, prop, unknow_none, context=None):
            res = {}
            for shop in self.browse(cr, uid, ids, context):
                if shop.default_storeview_integer_id:
                    rid = self.pool.get('magerp.storeviews').extid_to_oeid(cr, uid, shop.default_storeview_integer_id, shop.referential_id.id)
                    res[shop.id] = rid
                else:
                    res[shop.id] = False
            return res

        def export_images(self, cr, uid, ids, context=None):
            if context is None: context = {}
            start_date = time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            image_obj = self.pool.get('product.images')
            for shop in self.browse(cr, uid, ids):
                external_session = ExternalSession(shop.referential_id, shop)
                exportable_product_ids = self.read(cr, uid, shop.id, ['exportable_product_ids'], context=context)['exportable_product_ids']
                res = self.pool.get('product.product').get_exportable_images(cr, uid, external_session, exportable_product_ids, context=context)
                if res:
                    _logger.info("Creating %s images", len(res['to_create']))
                    _logger.info("Updating %s images", len(res['to_update']))
                    image_obj.update_remote_images(cr, uid, external_session, res['to_update']+res['to_create'], context)
                self.pool.get('product.images')._set_last_exported_date(cr, uid, external_session, start_date, context=context)
            return True

        #TODO refactor the ay to export images
        #No time for doing it now so I just overwrite the generic function
        #In order to use the actual implementation

        def export_resources(self, cr, uid, ids, resource_name, context=None):
            if resource_name == 'product.images':
                return self.export_images(cr, uid, ids, context=context)
            else:
                return super(sale_shop, self).export_resources(cr, uid, ids, resource_name, context=context)

        def _get_rootcategory(self, cr, uid, ids, name, value, context=None):
            res = {}
            for shop in self.browse(cr, uid, ids, context):
                if shop.root_category_id and shop.shop_group_id.referential_id:
                    rid = self.pool.get('product.category').extid_to_existing_oeid(
                        cr, uid, shop.shop_group_id.referential_id.id, shop.root_category_id)
                    res[shop.id] = rid
                else:
                    res[shop.id] = False
            return res

        def _set_rootcategory(self, cr, uid, id, name, value, fnct_inv_arg, context=None):
            ir_model_data_obj = self.pool.get('ir.model.data')
            shop = self.browse(cr, uid, id, context=context)
            if shop.root_category_id:
                model_data_id = self.pool.get('product.category').\
                extid_to_existing_oeid(cr, uid, shop.root_category_id, shop.referential_id.id, context=context)
                if model_data_id:
                    ir_model_data_obj.write(cr, uid, model_data_id, {'res_id' : value}, context=context)
                else:
                    raise except_osv(_('Warning!'),
                                     _('No external id found, are you sure that the referential are syncronized? '
                                       'Please contact your administrator. '
                                       '(more information in magentoerpconnect/sale.py)'))
            return True

        def _get_exportable_root_category_ids(self, cr, uid, ids, prop, unknow_none, context=None):
            res = {}
            res1 = self._get_rootcategory(cr, uid, ids, prop, unknow_none, context)
            for shop in self.browse(cr, uid, ids, context):
                res[shop.id] = res1[shop.id] and [res1[shop.id]] or []
            return res

        # xxx move to MagentoConnector._get_import_defaults_sale_shop
        @only_for_referential('magento')
        def _get_default_import_values(self, cr, uid, external_session, **kwargs):
            defaults = super(sale_shop, self)._get_default_import_values(cr, uid, external_session, **kwargs)
            if not defaults: defaults={}
            defaults.update({'magento_shop' : True})
            return defaults

        @only_for_referential('magento')
        @open_report
        def _export_inventory(self, *args, **kwargs):
            return super(sale_shop, self)._export_inventory(*args, **kwargs)

        _columns = {
            'default_storeview_integer_id':fields.integer('Magento default Storeview ID'), #This field can't be a many2one because store field will be mapped before creating storeviews
            'default_storeview_id':fields.function(_get_default_storeview_id, type="many2one", relation="magerp.storeviews", method=True, string="Default Storeview"),
            'root_category_id':fields.integer('Root product Category'), #This field can't be a many2one because store field will be mapped before creating category
            'magento_root_category':fields.function(_get_rootcategory, fnct_inv = _set_rootcategory, type="many2one", relation="product.category", string="Root Category"),
            'exportable_root_category_ids': fields.function(_get_exportable_root_category_ids, type="many2many", relation="product.category", method=True, string="Root Category"), #fields.function(_get_exportable_root_category_ids, type="many2one", relation="product.category", method=True, 'Exportable Root Categories'),
            'storeview_ids': fields.one2many('magerp.storeviews', 'shop_id', 'Store Views'),
            'exportable_product_ids': fields.function(_get_exportable_product_ids, method=True, type='one2many', relation="product.product", string='Exportable Products'),
            #TODO fix me, it's look like related field on a function fielf doesn't work.
            #'magento_shop': fields.related('referential_id', 'magento_referential',type="boolean", string='Magento Shop', readonly=True),
            'magento_shop': fields.boolean('Magento Shop', readonly=True),
            'allow_magento_order_status_push': fields.boolean('Allow Magento Order Status push', help='Allow to send back order status to Magento if order status changed in OpenERP first?'),
            'allow_magento_notification': fields.boolean('Allow Magento Notification', help='Allow Magento to notify customer with an e-mail when OpenERP change an order status, create an invoice or a delivery order on Magento.'),
        }

        _defaults = {
            'allow_magento_order_status_push': lambda * a: False,
            'allow_magento_notification': lambda * a: False,
        }

        def _get_magento_status(self, cr, uid, order, context=None):
            return ORDER_STATUS_MAPPING.get(order.state)

        def update_shop_orders(self, cr, uid, external_session, order, ext_id, context=None):
            if context is None: context = {}
            result = False
            if order.shop_id.allow_magento_order_status_push:
                sale_obj = self.pool.get('sale.order')
                #status update:
                status = self._get_magento_status(cr, uid, order, context=context)
                if status:
                    result = external_session.connection.call(
                        'sales_order.addComment',
                        [ext_id, status, '',
                         order.shop_id.allow_magento_notification])
                    #TODO REMOVE ME
                    # If status has changed into OERP and the order need_to_update,
                    # then we consider the update is done
                    # remove the 'need_to_update': True
                    if order.need_to_update:
                        sale_obj.write(
                            cr, uid, order.id, {'need_to_update': False})
            return result

        def _sale_shop(self, cr, uid, callback, context=None):
            if context is None:
                context = {}
            proxy = self.pool.get('sale.shop')
            domain = [ ('magento_shop', '=', True), ('auto_import', '=', True) ]

            ids = proxy.search(cr, uid, domain, context=context)
            if ids:
                callback(cr, uid, ids, context=context)

            # tools.debug(callback)
            # tools.debug(ids)
            return True

        # Schedules functions ============ #
        def run_import_orders_scheduler(self, cr, uid, context=None):
            self._sale_shop(cr, uid, self.import_orders, context=context)

        def run_update_orders_scheduler(self, cr, uid, context=None):
            self._sale_shop(cr, uid, self.update_orders, context=context)

        def run_export_catalog_scheduler(self, cr, uid, context=None):
            self._sale_shop(cr, uid, self.export_catalog, context=context)

        def run_export_stock_levels_scheduler(self, cr, uid, context=None):
            self._sale_shop(cr, uid, self.export_inventory, context=context)

        def run_update_images_scheduler(self, cr, uid, context=None):
            self._sale_shop(cr, uid, self.export_images, context=context)

        def run_export_shipping_scheduler(self, cr, uid, context=None):
            self._sale_shop(cr, uid, self.export_shipping, context=context)

        def run_import_check_need_to_update(self, cr, uid, context=None):
            self._sale_shop(cr, uid, self.check_need_to_update, context=context)

    class sale_order(Model):
        _inherit = "sale.order"
        _columns = {
            'magento_incrementid': fields.char('Magento Increment ID', size=32),
            'magento_storeview_id': fields.many2one('magerp.storeviews', 'Magento Store View'),
            'is_magento': fields.related(
                'shop_id', 'referential_id', 'magento_referential',
                type='boolean',
                string='Is a Magento Sale Order')
            }

        def _auto_init(self, cr, context=None):
            tools.drop_view_if_exists(cr, 'sale_report')
            cr.execute("ALTER TABLE sale_order_line ALTER COLUMN discount TYPE numeric(16,6);")
            cr.execute("ALTER TABLE account_invoice_line ALTER COLUMN discount TYPE numeric(16,6);")
            self.pool.get('sale.report').init(cr)
            super(sale_order, self)._auto_init(cr, context)


        def _get_payment_information(self, cr, uid, external_session, order_id, resource, context=None):
            """
            Parse the external resource and return a dict of data converted
            """
            vals = super(sale_order, self)._get_payment_information(cr, uid, external_session, order_id, resource, context=context)
            payment_info = resource.get('payment')
            if payment_info and payment_info.get('amount_paid'):
                vals['paid'] = True
                vals['amount'] = float(payment_info['amount_paid'])
            return vals

        def _chain_cancel_orders(self, cr, uid, external_id, external_referential_id, defaults=None, context=None):
            """ Get all the chain of edited orders (an edited order is canceled on Magento)
             and cancel them on OpenERP. If an order cannot be canceled (confirmed for example)
             A request is created to inform the user.
            """
            if context is None:
                context = {}
            conn = context.get('conn_obj', False)
            parent_list = []
            # get all parents orders (to cancel) of the sale orders
            parent = conn.call('sales_order.get_parent', [external_id])
            while parent:
                parent_list.append(parent)
                parent = conn.call('sales_order.get_parent', [parent])

            wf_service = netsvc.LocalService("workflow")
            for parent_incr_id in parent_list:
                canceled_order_id = self.extid_to_existing_oeid(cr, uid, parent_incr_id, external_referential_id)
                if canceled_order_id:
                    try:
                        wf_service.trg_validate(uid, 'sale.order', canceled_order_id, 'cancel', cr)
                        self.log(cr, uid, canceled_order_id, "order %s canceled when updated from external system" % (canceled_order_id,))
                        _logger.info("Order %s canceled when updated from external system because it has been replaced by a new one", canceled_order_id)
                    except except_osv, e:
                        #TODO: generic reporting of errors in magentoerpconnect
                        # except if the sale order has been confirmed for example, we cannot cancel the order
                        to_cancel_order_name = self.read(cr, uid, canceled_order_id, ['name'])['name']
                        request = self.pool.get('res.request')
                        summary = _(("The sale order %s has been replaced by the sale order %s on Magento.\n"
                                     "The sale order %s has to be canceled on OpenERP but it is currently impossible.\n\n"
                                     "Error:\n"
                                     "%s\n"
                                     "%s")) % (parent_incr_id,
                                              external_id,
                                              to_cancel_order_name,
                                              e.name,
                                              e.value)
                        request.create(cr, uid,
                                       {'name': _("Could not cancel sale order %s during Magento's sale orders import") % (to_cancel_order_name,),
                                        'act_from': uid,
                                        'act_to': uid,
                                        'body': summary,
                                        'priority': '2'
                                        })

    #NEW FEATURE

    #TODO reimplement chain cancel orders
    #                # if a created order has a relation_parent_real_id, the new one replaces the original, so we have to cancel the old one
    #                if data[0].get('relation_parent_real_id', False): # data[0] because orders are imported one by one so data always has 1 element
    #                    self._chain_cancel_orders(order_cr, uid, ext_order_id, external_referential_id, defaults=defaults, context=context)

        # XXX a deplacer dans MagentoConnector
        def _get_filter(self, cr, uid, external_session, step, previous_filter=None, context=None):
            magento_storeview_ids=[]
            shop = external_session.sync_from_object
            for storeview in shop.storeview_ids:
                magento_storeview_id = self.pool.get('magerp.storeviews').get_extid(cr, uid, storeview.id, shop.referential_id.id, context={})
                if magento_storeview_id:
                    magento_storeview_ids.append(magento_storeview_id)

            mag_filter = {
                'state': {'neq': 'canceled'},
                'store_id': {'in': magento_storeview_ids},
                }

            if shop.import_orders_from_date:
                mag_filter.update({'created_at' : {'gt': shop.import_orders_from_date}})
            return {
                'imported': False,
                'limit': step,
                'filters': mag_filter,
            }

        def create_onfly_partner(self, cr, uid, external_session, resource, mapping, defaults, context=None):
            """
            As magento allow guest order we have to create an on fly partner without any external id
            """
            if not defaults: defaults={}
            local_defaults = defaults.copy()

            resource['firstname'] = resource['customer_firstname']
            resource['lastname'] = resource['customer_lastname']
            resource['email'] = resource['customer_email']

            shop = external_session.sync_from_object
            partner_defaults = {'website_id': shop.shop_group_id.id}
            res = self.pool.get('res.partner')._record_one_external_resource(cr, uid, external_session, resource,\
                                    mapping=mapping, defaults=partner_defaults, context=context)
            partner_id = res.get('create_id') or res.get('write_id')

            local_defaults['partner_id'] = partner_id
            for address_key in ['partner_invoice_id', 'partner_shipping_id']:
                if not defaults.get(address_key): local_defaults[address_key] = {}
                local_defaults[address_key]['partner_id'] = partner_id
            return local_defaults

        @only_for_referential('magento')
        def _transform_one_resource(self, cr, uid, external_session, convertion_type, resource, mapping, mapping_id, \
                         mapping_line_filter_ids=None, parent_data=None, previous_result=None, defaults=None, context=None):
            resource = self.clean_magento_resource(cr, uid, resource, context=context)
            resource = self.clean_magento_items(cr, uid, resource, context=context)
            for line in mapping[mapping_id]['mapping_lines']:
                if line['name'] == 'customer_id' and not resource.get('customer_id'):
                    #If there is not partner it's a guest order
                    #So we remove the useless information
                    #And create a partner on fly and set the data in the default value
                    #We only do this if the customer_id is in the mapping line
                    #Indeed when we check if a sale order exist only the name is asked for convertion
                    resource.pop('customer_id', None)
                    resource['billing_address'].pop('customer_id', None)
                    resource['shipping_address'].pop('customer_id', None)
                    defaults = self.create_onfly_partner(cr, uid, external_session, resource, mapping, defaults, context=context)

            return super(sale_order, self)._transform_one_resource(cr, uid, external_session, convertion_type, resource,\
                     mapping, mapping_id,  mapping_line_filter_ids=mapping_line_filter_ids, parent_data=parent_data,\
                     previous_result=previous_result, defaults=defaults, context=context)

        # XXX move to MagentoConnector _ext_search_sale_order
        @only_for_referential('magento')
        def _get_external_resource_ids(self, cr, uid, external_session, resource_filter=None, mapping=None, mapping_id=None, context=None):
            res = super(sale_order, self)._get_external_resource_ids(cr, uid, external_session, resource_filter=resource_filter, mapping=mapping, mapping_id=mapping_id, context=context)
            order_ids_to_import=[]
            for external_id in res:
                existing_id = self.get_oeid(cr, uid, external_id, external_session.referential_id.id, context=context)
                if existing_id:
                    external_session.logger.info(_("the order %s already exist in OpenERP") % (external_id,))
                    self.ext_set_resource_as_imported(cr, uid, external_session, external_id, mapping=mapping, mapping_id=mapping_id, context=context)
                else:
                    order_ids_to_import.append(external_id)
            return order_ids_to_import

        # xxx a deplacer dans MagentoConnector _record_one_sale_order
        @only_for_referential('magento')
        def _record_one_external_resource(self, cr, uid, external_session, resource, defaults=None, mapping=None, mapping_id=None, context=None):
            res = super(sale_order, self)._record_one_external_resource(cr, uid, external_session, resource, defaults=defaults, mapping=mapping, mapping_id=mapping_id, context=context)
            external_id = resource['increment_id'] # TODO it will be better to not hardcode this parameter
            self.ext_set_resource_as_imported(cr, uid, external_session, external_id, mapping=mapping, mapping_id=mapping_id, context=context)
            return res

        @only_for_referential('magento')
        def _check_need_to_update_single(self, cr, uid, external_session, order, context=None):
            """
            For one order, check on Magento if it has been paid since last
            check. If so, it will launch the defined flow based on the
            payment type (validate order, invoice, ...)

            :param browse_record order: browseable sale.order
            :param Connection conn: connection with Magento
            :return: True
            """

            #TODO improve me and replace me by a generic function in connector_ecommerce
            #Only the call to magento should be here

            model_data_obj = self.pool.get('ir.model.data')
            # check if the status has changed in Magento
            # We don't use oeid_to_extid function cause it only handles integer ids
            # Magento can have something like '100000077-2'
            model_data_ids = model_data_obj.search(
                cr, uid,
                [('model', '=', self._name),
                 ('res_id', '=', order.id),
                 ('referential_id', '=', order.shop_id.referential_id.id)],
                context=context)

            if model_data_ids:
                prefixed_id = model_data_obj.read(
                    cr, uid, model_data_ids[0], ['name'], context=context)['name']
                ext_id = self.id_from_prefixed_id(prefixed_id)
            else:
                return False

            resource = external_session.connection.call('sales_order.info', [ext_id])

            if resource['status'] == 'canceled':
                wf_service = netsvc.LocalService("workflow")
                wf_service.trg_validate(uid, 'sale.order', order.id, 'cancel', cr)
                updated = True
                self.log(cr, uid, order.id, "order %s canceled when updated from external system" % (order.id,))
            # If the order isn't canceled and was waiting for a payment,
            # so we follow the standard flow according to ext_payment_method:
            else:
                updated = self.paid_and_update(cr, uid, external_session, order.id, resource, context=context)
                if updated:
                    self.log(
                        cr, uid, order.id,
                        "order %s paid when updated from external system" %
                        (order.id,))
            # Untick the need_to_update if updated (if so was canceled in magento
            # or if it has been paid through magento)
            if updated:
                self.write(cr, uid, order.id, {'need_to_update': False})
            cr.commit() #Ugly we should not commit in the current cursor
            return True

    ########################################################################################################################
    #
    #           CODE THAT CLEAN MAGENTO DATA BEFORE IMPORTING IT THE BEST WILL BE TO REFACTOR MAGENTO API
    #
    ########################################################################################################################


        def _merge_sub_items(self, cr, uid, product_type, top_item, child_items, context=None):
            """
            Manage the sub items of the magento sale order lines. A top item contains one
            or many child_items. For some product types, we want to merge them in the main
            item, or keep them as order line.

            This method has to stay because it allow to customize the behavior of the sale
            order according to the product type.

            A list may be returned to add many items (ie to keep all child_items as items.

            :param top_item: main item (bundle, configurable)
            :param child_items: list of childs of the top item
            :return: item or list of items
            """
            if product_type == 'configurable':
                item = top_item.copy()
                # For configurable product all information regarding the price is in the configurable item
                # In the child a lot of information is empty, but contains the right sku and product_id
                # So the real product_id and the sku and the name have to be extracted from the child
                for field in ['sku', 'product_id', 'name']:
                    item[field] = child_items[0][field]
                return item
            return top_item

        def clean_magento_items(self, cr, uid, resource, context=None):
            """
            Method that clean the sale order line given by magento before importing it

            This method has to stay here because it allow to customize the behavior of the sale
            order.

            """
            child_items = {}  # key is the parent item id
            top_items = []

            # Group the childs with their parent
            for item in resource['items']:
                if item.get('parent_item_id'):
                    child_items.setdefault(item['parent_item_id'], []).append(item)
                else:
                    top_items.append(item)

            all_items = []
            for top_item in top_items:
                if top_item['item_id'] in child_items:
                    item_modified = self._merge_sub_items(cr, uid,
                                                          top_item['product_type'],
                                                          top_item,
                                                          child_items[top_item['item_id']],
                                                          context=context)
                    if not isinstance(item_modified, list):
                        item_modified = [item_modified]
                    all_items.extend(item_modified)
                else:
                    all_items.append(top_item)

            resource['items'] = all_items
            return resource

        def clean_magento_resource(self, cr, uid, resource, context=None):
            """
            Magento copy each address in a address sale table.
            Keeping the extid of this table 'address_id' is useless because we don't need it later
            And it's dangerous because we will have various external id for the same resource and the same referential
            Getting the ext_id of the table customer address is also not posible because Magento LIE
            Indeed if a customer create a new address on fly magento will give us the default id instead of False
            So it better to NOT trust magento and not based the address on external_id
            To avoid any erreur we remove the key
            """
            for remove_key in ['customer_address_id', 'address_id']:
                for key in ['billing_address', 'shipping_address']:
                    if remove_key in resource[key]: del resource[key][remove_key]

            # For really strange and unknow reason magento want to play with me and make me some joke.
            # Depending of the customer installation some time the field customer_id is equal to NONE
            # in the sale order and sometime it's equal to NONE in the address but at least the
            # the information is correct in one of this field
            # So I make this ugly code to try to fix it.
            if not resource.get('customer_id'):
                if resource['billing_address'].get('customer_id'):
                    resource['customer_id'] = resource['billing_address']['customer_id']
            else:
                if not resource['billing_address'].get('customer_id'):
                    resource['billing_address']['customer_id'] = resource['customer_id']
                if not resource['shipping_address'].get('customer_id'):
                    resource['shipping_address']['customer_id'] = resource['customer_id']
            return resource


    class sale_order_line(Model):
        _inherit = 'sale.order.line'
        _columns = {
            # Rised the precision of the sale.order.line discount field
            # from 2 to 3 digits in order to be able to have the same amount as Magento.
            # Example: Magento has a sale line of 299€ and 150€ of discount, so a line at 149€.
            # We translate it to a percent in the openerp sale order
            # With a 2 digits precision, we can have 50.17 % => 148.99 or 50.16% => 149.02.
            # Rise the digits to 3 allows to have 50.167% => 149€
            'discount': fields.float('Discount (%)', digits=(16, 3), readonly=True, states={'draft': [('readonly', False)]}),
            }


# transfered from invoice.py ###############################


class account_invoice(orm.Model):
    _inherit = 'account.invoice'

    #TODO instead of calling again the sale order information
    # it will be better to store the ext_id of each sale order line
    #Moreover some code should be share between the partial export of picking and invoice
    def add_invoice_line(self, cr, uid, lines, line, context=None):
        """ A line to add in the invoice is a dict with : product_id and product_qty keys."""
        line_info = {'product_id': line.product_id.id,
                     'product_qty': line.quantity,
                     }
        lines.append(line_info)
        return lines

    def get_invoice_items(self, cr, uid, external_session, invoice_id, order_increment_id, context=None):
        invoice = self.browse(cr, uid, invoice_id, context=context)
        balance = invoice.sale_ids[0].amount_total - invoice.amount_total
        precision = self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')
        item_qty = {}
        if round(balance, precision):
            order_items = external_session.connection.call('sales_order.info', [order_increment_id])['items']
            product_2_item = {}
            for item in order_items:
                product_2_item.update({self.pool.get('product.product').get_oeid(cr, uid, item['product_id'],
                                        external_session.referential_id.id, context={}): item['item_id']})

            lines = []
            # get product and quantities to invoice from the invoice
            for line in invoice.invoice_line:
                lines = self.add_invoice_line(cr, uid, lines, line, context)

            for line in lines:
                #Only export product that exist in the original sale order
                if product_2_item.get(line['product_id']):
                    if item_qty.get(product_2_item[line['product_id']], False):
                        item_qty[product_2_item[line['product_id']]] += line['product_qty']
                    else:
                        item_qty.update({product_2_item[line['product_id']]: line['product_qty']})
        return item_qty

    def map_magento_order(self, cr, uid, external_session, invoice_id, order_increment_id, context=None):
        #TODO Error should be catch by the external report system (need some improvement before)
        #For now error are just logged into the OpenERP log file
        try:
            external_session.logger.warning('Try to map the invoice with an existing order')
            invoice_ids = external_session.connection.call('sales_order.get_invoice_ids', [order_increment_id])
            #TODO support mapping for partiel invoice if needed
            if len(invoice_ids) == 1:
                external_session.logger.info(
                    'Success to map the invoice %s with an existing order for the order %s.'
                    %(invoice_ids[0], order_increment_id))
                return invoice_ids[0]
            else:
                external_session.logger.error(
                    'Failed to map the invoice %s with an existing order for the order %s. Too many invoice found'
                    %(invoice_ids[0], order_increment_id))
                return False
        except Exception, e:
            external_session.logger.error(
                'Failed to map the invoice with an existing order for the order %s. Error : %s'
                %(order_increment_id, e))
        return False

    def create_magento_invoice(self, cr, uid, external_session, invoice_id, order_increment_id, context=None):
        item_qty = self.get_invoice_items(cr, uid, external_session, invoice_id, order_increment_id, context=context)
        try:
            return external_session.connection.call('sales_order_invoice.create', [order_increment_id,
                                                     item_qty, _('Invoice Created'), False, False])
        except Exception, e:
            external_session.logger.warning(
                'Can not create the invoice for the order %s in the external system. Error : %s'
                %(order_increment_id, e))
            invoice_id = self.map_magento_order(cr, uid, external_session, invoice_id, order_increment_id, context=context)
            if invoice_id:
                return invoice_id
            else:
                raise except_osv(_('Magento Error'), _('Failed to synchronize Magento invoice with OpenERP invoice'))

    def ext_create(self, cr, uid, external_session, resources, mapping=None, mapping_id=None, context=None):
        ext_create_ids={}
        for resource_id, resource in resources.items():
            res = self.ext_create_one_invoice(cr, uid, external_session, resource_id, resource, context=context)
            if res:
                ext_create_ids[resource_id] = res
        return ext_create_ids

    def ext_create_one_invoice(self, cr, uid, external_session, resource_id, resource, context=None):
        resource = resource[resource.keys()[0]]
        if resource['type'] == 'out_invoice':
            return self.create_magento_invoice(cr, uid, external_session,
                                resource_id, resource['order_increment_id'], context=context)
        return False

    def _export_one_invoice(self, cr, uid, invoice, context=None):
        if invoice.sale_ids:
            sale = invoice.sale_ids[0]
            referential = sale.shop_id.referential_id
            if referential and referential.type_name == 'Magento':
                ext_id = invoice.get_extid(referential.id)
                if ext_id:
                    return ext_id
                else:
                    external_session = ExternalSession(referential, sale.shop_id)
                    return self._export_one_resource(cr, uid, external_session, invoice.id,
                                                     context=context)

    def export_invoice(self, cr, uid, ids, context=None):
        for invoice in self .browse(cr, uid, ids, context=context):
            self._export_one_invoice(cr, uid, invoice, context=context)
        return True


# transfered from product.py ###############################


#Enabling this to True will put all custom attributes into One page in
#the products view
GROUP_CUSTOM_ATTRS_TOGETHER = False


#TODO find a good method to replace all of the special caracter allowed by magento as name for product fields
special_character_to_replace = [
    (u"\xf8", u"diam"),
    (u'\xb5', u'micro'),
    (u'\xb2', u'2'),
    (u'\u0153', u'oe'),
    (u'\uff92', u'_'),
    (u'\ufffd', u'_'),
]

def convert_to_ascii(my_unicode):
    '''Convert to ascii, with clever management of accents (é -> e, è -> e)'''
    if isinstance(my_unicode, unicode):
        my_unicode_with_ascii_chars_only = ''.join((char for char in unicodedata.normalize('NFD', my_unicode) if unicodedata.category(char) != 'Mn'))
        for special_caracter in special_character_to_replace:
            my_unicode_with_ascii_chars_only = my_unicode_with_ascii_chars_only.replace(special_caracter[0], special_caracter[1])
        return str(my_unicode_with_ascii_chars_only)
    # If the argument is already of string type, we return it with the same value
    elif isinstance(my_unicode, str):
        return my_unicode
    else:
        return False

class magerp_product_category_attribute_options(MagerpModel):
    _name = "magerp.product_category_attribute_options"
    _description = "Option products category Attributes"
    _rec_name = "label"

    def _get_default_option(self, cr, uid, field_name, value, context=None):
        res = self.search(cr, uid, [['attribute_name', '=', field_name], ['value', '=', value]], context=context)
        return res and res[0] or False


    def get_create_option_id(self, cr, uid, value, attribute_name, context=None):
        id = self.search(cr, uid, [['attribute_name', '=', attribute_name], ['value', '=', value]], context=context)
        if id:
            return id[0]
        else:
            return self.create(cr, uid, {
                                'value': value,
                                'attribute_name': attribute_name,
                                'label': value.replace('_', ' '),
                                }, context=context)

    #TODO to finish : this is just the start of the implementation of attributs for category
    _columns = {
        #'attribute_id':fields.many2one('magerp.product_attributes', 'Attribute'),
        'attribute_name':fields.char(string='Attribute Code',size=64),
        'value':fields.char('Value', size=200),
        #'ipcast':fields.char('Type cast', size=50),
        'label':fields.char('Label', size=100),
        }


class product_category(MagerpModel):
    _inherit = "product.category"

    def _merge_with_default_values(self, cr, uid, external_session, ressource, vals, sub_mapping_list, defaults=None, context=None):
        vals = super(product_category, self)._merge_with_default_values(cr, uid, external_session, ressource, vals, sub_mapping_list, defaults=defaults, context=context)
        #some time magento category doesn't have a name
        if not vals.get('name'):
            vals['name'] = 'Undefined'
        return vals

    def _get_default_export_values(self, *args, **kwargs):
        defaults = super(product_category, self)._get_default_export_values(*args, **kwargs)
        if defaults == None: defaults={}
        defaults.update({'magento_exportable': True})
        return defaults

    def multi_lang_read(self, cr, uid, external_session, ids, fields_to_read, langs, resources=None, use_multi_lang = True, context=None):
        return super(product_category, self).multi_lang_read(cr, uid, external_session, ids, fields_to_read, langs,
                                                            resources=resources,
                                                            use_multi_lang = False,
                                                            context=context)

    def ext_create(self, cr, uid, external_session, resources, mapping=None, mapping_id=None, context=None):
        ext_create_ids={}
        storeview_to_lang = context['storeview_to_lang']
        main_lang = context['main_lang']
        for resource_id, resource in resources.items():
            #Move this part of code in a python lib
            parent_id = resource[main_lang]['parent_id']
            del resource[main_lang]['parent_id']
            ext_id = external_session.connection.call('catalog_category.create', [parent_id, resource[main_lang]])
            for storeview, lang in storeview_to_lang.items():
                external_session.connection.call('catalog_category.update', [ext_id, resource[lang], storeview])
            ext_create_ids[resource_id] = ext_id
        return ext_create_ids


    def ext_update(self, cr, uid, external_session, resources, mapping=None, mapping_id=None, context=None):
        ext_update_ids={}
        storeview_to_lang = context['storeview_to_lang']
        main_lang = context['main_lang']
        for resource_id, resource in resources.items():
            #Move this part of code in a python lib
            ext_id = resource[main_lang]['ext_id']
            del resource[main_lang]['ext_id']
            parent_id = resource[main_lang]['parent_id']
            del resource[main_lang]['parent_id']
            external_session.connection.call('catalog_category.update', [ext_id, resource[main_lang], False])
            external_session.connection.call('oerp_catalog_category.move', [ext_id, parent_id])
            for storeview, lang in storeview_to_lang.items():
                del resource[lang]['ext_id']
                external_session.connection.call('catalog_category.update', [ext_id, resource[lang], storeview])
            ext_update_ids[resource_id] = ext_id
        return ext_update_ids

    _columns = {
        'magerp_fields' : fields.serialized('Magento Product Categories Extra Fields'),
        'create_date': fields.datetime('Created date', readonly=True),
        'write_date': fields.datetime('Updated date', readonly=True),
        'magento_exportable':fields.boolean('Export to Magento'),
        'updated':fields.boolean('To synchronize', help="Set if the category underwent a change & has to be synched."),
        #*************** Magento Fields ********************
        #==== General Information ====
        'level': fields.integer('Level', readonly=True),
        'magento_parent_id': fields.integer('Magento Parent', readonly=True), #Key Changed from parent_id
        'is_active': fields.boolean('Active?', help="Indicates whether active in magento"),
        'description': fields.text('Description'),
        'image': fields.binary('Image'),
        'image_name':fields.char('File Name', size=100),
        'meta_title': fields.char('Title (Meta)', size=75),
        'meta_keywords': fields.text('Meta Keywords'),
        'meta_description': fields.text('Meta Description'),
        'url_key': fields.char('URL-key', size=100), #Readonly
        #==== Display Settings ====
        'display_mode': fields.selection([
                    ('PRODUCTS', 'Products Only'),
                    ('PAGE', 'Static Block Only'),
                    ('PRODUCTS_AND_PAGE', 'Static Block & Products')], 'Display Mode', required=True),
        'is_anchor': fields.boolean('Anchor?'),
        'use_default_available_sort_by': fields.boolean('Default Config For Available Sort By', help="Use default config for available sort by"),
        # 'available_sort_by': fields.sparse(type='many2many', relation='magerp.product_category_attribute_options', string='Available Product Listing (Sort By)', serialization_field='magerp_fields', domain="[('attribute_name', '=', 'sort_by'), ('value', '!=','None')]"),
        # 'default_sort_by': fields.many2one('magerp.product_category_attribute_options', 'Default Product Listing Sort (Sort By)', domain="[('attribute_name', '=', 'sort_by')]", require=True),
        'magerp_stamp':fields.datetime('Magento stamp'),
        'include_in_menu': fields.boolean('Include in Navigation Menu'),
        # 'page_layout': fields.many2one('magerp.product_category_attribute_options', 'Page Layout', domain="[('attribute_name', '=', 'page_layout')]"),
        }

    _defaults = {
        'display_mode':lambda * a:'PRODUCTS',
        'use_default_available_sort_by': lambda * a:True,
        # 'default_sort_by': lambda self,cr,uid,c: self.pool.get('magerp.product_category_attribute_options')._get_default_option(cr, uid, 'sort_by', 'None', context=c),
        'level':lambda * a:1,
        'include_in_menu': lambda * a:True,
        # 'page_layout': lambda self,cr,uid,c: self.pool.get('magerp.product_category_attribute_options')._get_default_option(cr, uid, 'page_layout', 'None', context=c),
        }

    def write(self, cr, uid, ids, vals, context=None):
        if not 'magerp_stamp' in vals.keys():
            vals['magerp_stamp'] = time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        return super(product_category, self).write(cr, uid, ids, vals, context)

    # XXX reimplement in Connector as _ext_search_product_category
    def _get_external_resource_ids(self, cr, uid, external_session, resource_filter=None, mapping=None, context=None):
        def get_child_ids(tree):
            result=[]
            result.append(tree['category_id'])
            for categ in tree['children']:
                result += get_child_ids(categ)
            return result
        ids=[]
        confirmation = external_session.connection.call('catalog_category.currentStore', [0])   #Set browse to root store
        if confirmation:
            categ_tree = external_session.connection.call('catalog_category.tree')             #Get the tree
            ids = get_child_ids(categ_tree)
        return ids


class magerp_product_attributes(MagerpModel):
    _name = "magerp.product_attributes"
    _description = "Attributes of products"
    _rec_name = "attribute_code"

    def _get_group(self, cr, uid, ids, prop, unknow_none, context=None):
        res = {}
        for attribute in self.browse(cr, uid, ids, context):
            res[attribute.id] = self.pool.get('magerp.product_attribute_groups').extid_to_existing_oeid(cr, uid, attribute.group_id, attribute.referential_id.id)
        return res

    _columns = {
        'attribute_code':fields.char('Code', size=200),
        'magento_id':fields.integer('ID'),
        'set_id':fields.integer('Attribute Set'),
        'options':fields.one2many('magerp.product_attribute_options', 'attribute_id', 'Attribute Options'),
        #'set':fields.function(_get_set, type="many2one", relation="magerp.product_attribute_set", method=True, string="Attribute Set"), This field is invalid as attribs have m2m relation
        'frontend_input':fields.selection([
                                           ('text', 'Text'),
                                           ('textarea', 'Text Area'),
                                           ('select', 'Selection'),
                                           ('multiselect', 'Multi-Selection'),
                                           ('boolean', 'Yes/No'),
                                           ('date', 'Date'),
                                           ('price', 'Price'),
                                           ('media_image', 'Media Image'),
                                           ('gallery', 'Gallery'),
                                           ('weee', 'Fixed Product Tax'),
                                           ('file', 'File'), #this option is not a magento native field it will be better to found a generic solutionto manage this kind of custom option
                                           ('weight', 'Weight'),
                                           ], 'Frontend Input'
                                          ),
        'frontend_class':fields.char('Frontend Class', size=100),
        'backend_model':fields.char('Backend Model', size=200),
        'backend_type':fields.selection([
                                         ('static', 'Static'),
                                         ('varchar', 'Varchar'),
                                         ('text', 'Text'),
                                         ('decimal', 'Decimal'),
                                         ('int', 'Integer'),
                                         ('datetime', 'Datetime')], 'Backend Type'),
        'frontend_label':fields.char('Label', size=100),
        'is_visible_in_advanced_search':fields.boolean('Visible in advanced search?', required=False),
        'is_global':fields.boolean('Global ?', required=False),
        'is_filterable':fields.boolean('Filterable?', required=False),
        'is_comparable':fields.boolean('Comparable?', required=False),
        'is_visible':fields.boolean('Visible?', required=False),
        'is_searchable':fields.boolean('Searchable ?', required=False),
        'is_user_defined':fields.boolean('User Defined?', required=False),
        'is_configurable':fields.boolean('Configurable?', required=False),
        'is_visible_on_front':fields.boolean('Visible (Front)?', required=False),
        'is_used_for_price_rules':fields.boolean('Used for pricing rules?', required=False),
        'is_unique':fields.boolean('Unique?', required=False),
        'is_required':fields.boolean('Required?', required=False),
        'position':fields.integer('Position', required=False),
        'group_id': fields.integer('Group') ,
        'group':fields.function(_get_group, type="many2one", relation="magerp.product_attribute_groups", method=True, string="Attribute Group"),
        'apply_to': fields.char('Apply to', size=200),
        'default_value': fields.char('Default Value', size=10),
        'note':fields.char('Note', size=200),
        'entity_type_id':fields.integer('Entity Type'),
        'referential_id':fields.many2one('external.referential', 'Magento Instance', readonly=True),
        #These parameters are for automatic management
        'field_name':fields.char('Open ERP Field name', size=100),
        'attribute_set_info':fields.text('Attribute Set Information'),
        'based_on':fields.selection([('product_product', 'Product Product'), ('product_template', 'Product Template')], 'Based On'),
        }

    _defaults = {'based_on': lambda*a: 'product_template',
                 }
    #mapping magentofield:(openerpfield,typecast,)
    #have an entry for each mapped field
    _no_create_list = ['product_id',
                       'name',
                       'description',
                       'short_description',
                       'sku',
                       'weight',
                       'category_ids',
                       'price',
                       'cost',
                       'set',
                       'ean',
                       ]
    _translatable_default_codes = ['description',
                                   'meta_description',
                                   'meta_keyword',
                                   'meta_title',
                                   'name',
                                   'short_description',
                                   'url_key',
                                   ]
    _not_store_in_json = ['minimal_price',
                          'special_price',
                          'description',
                          'meta_description',
                          'meta_keyword',
                          'meta_title',
                          'name',
                          'short_description',
                          'url_key',
                          ]
    _type_conversion = {'':'char',
                        'text':'char',
                        'textarea':'text',
                        'select':'many2one',
                        'date':'date',
                        'price':'float',
                        'media_image':'binary',
                        'gallery':'binary',
                        'multiselect':'many2many',
                        'boolean':'boolean',
                        'weee':'char',
                        False:'char',
                        'file':'char', #this option is not a magento native field it will be better to found a generic solutionto manage this kind of custom option
                        }
    _type_casts = {'':'unicode',
                   'text':'unicode',
                   'textarea':'unicode',
                   'select':'unicode',
                   'date':'unicode',
                   'price':'float',
                   'media_image':'False',
                   'gallery':'False',
                   'multiselect':'list',
                   'boolean':'int',
                   'weee':'unicode',
                   False:'unicode',
                   'file':'unicode', #this option is not a magento native field it will be better to found a generic solutionto manage this kind of custom option
                   }
    _variant_fields = ['color',
                       'dimension',
                       'visibility',
                       'special_price',
                       'special_price_from_date',
                       'special_price_to_date',
                       ]


    #For some field you can specify the syncronisation way
    #in : Magento => OpenERP
    #out : Magento <= OpenERP
    #in_out (default_value) : Magento <=> OpenERP
    #TODO check if this field have to be in only one way and if yes add this feature
    _sync_way = {'has_options' : 'in',
                 'tier_price': 'in',
                 'special_price' : 'in',
                 }

    def _is_attribute_translatable(self, vals):
        """Tells if field associated to attribute should be translatable or not.
        For now we are using a default list, later we could say that any attribute
        which scope in Magento is 'store' should be translated."""
        if vals['attribute_code'] in self._translatable_default_codes:
            return True
        else:
            return False

    def write(self, cr, uid, ids, vals, context=None):
        """Will recreate the mapping attributes, beware if you customized some!"""
        if context is None:
            context = {}

        if type(ids) == int:
            ids = [ids]
        result = super(magerp_product_attributes, self).write(cr, uid, ids, vals, context)
        model_ids = self.pool.get('ir.model').search(cr, uid, [('model', 'in', ['product.product', 'product.template'])])
        product_model_id = self.pool.get('ir.model').search(cr, uid, [('model', 'in', ['product.product'])])[0]
        referential_id = context.get('referential_id', False)
        if referential_id:
            for id in ids:
                all_vals = self.read(cr, uid, id, [], context)

                #Fetch Options
                if 'frontend_input' in all_vals.keys() and all_vals['frontend_input'] in ['select', 'multiselect']:
                    core_imp_conn = self.pool.get('external.referential').external_connection(cr, uid, [referential_id])
                    options_data = core_imp_conn.call('ol_catalog_product_attribute.options', [all_vals['magento_id']])
                    if options_data:
                        self.pool.get('magerp.product_attribute_options').data_to_save(cr, uid, options_data, update=True, context={'attribute_id': id, 'referential_id': referential_id})


                field_name = all_vals['field_name']
                #TODO refactor me it will be better to add a one2many between the magerp_product_attributes and the ir.model.fields
                field_ids = self.pool.get('ir.model.fields').search(cr, uid, [('name', '=', field_name), ('model_id', 'in', model_ids)])
                if field_ids:
                    self._create_mapping(cr, uid, self._type_conversion[all_vals.get('frontend_input', False)], field_ids[0], field_name, referential_id, product_model_id, all_vals, id)
        return result

    def create(self, cr, uid, vals, context=None):
        """Will create product.template new fields accordingly to Magento product custom attributes and also create mappings for them"""
        if context is None:
            context = {}
        if not vals['attribute_code'] in self._no_create_list:
            field_name = "x_magerp_" + vals['attribute_code']
            field_name = convert_to_ascii(field_name)
            vals['field_name']= field_name
        if 'attribute_set_info' in vals.keys():
            attr_set_info = eval(vals.get('attribute_set_info',{}))
            for each_key in attr_set_info.keys():
                vals['group_id'] = attr_set_info[each_key].get('group_id', False)

        crid = super(magerp_product_attributes, self).create(cr, uid, vals, context)
        if not vals['attribute_code'] in self._no_create_list:
            #If the field has to be created
            if crid:
                #Fetch Options
                if 'frontend_input' in vals.keys() and vals['frontend_input'] in ['select',  'multiselect']:
                    core_imp_conn = self.pool.get('external.referential').external_connection(cr, uid, vals['referential_id'])
                    options_data = core_imp_conn.call('ol_catalog_product_attribute.options', [vals['magento_id']])
                    if options_data:
                        self.pool.get('magerp.product_attribute_options').data_to_save(cr, uid, options_data, update=False, context={'attribute_id': crid, 'referential_id': vals['referential_id']})

                #Manage fields
                if vals['attribute_code'] and vals.get('frontend_input', False):
                    #Code for dynamically generating field name and attaching to this
                    if vals['attribute_code'] in self._variant_fields:
                        model_name='product.product'
                    else:
                        model_name='product.template'

                    model_id = self.pool.get('ir.model').search(cr, uid, [('model', '=', model_name)])

                    if model_id and len(model_id) == 1:
                        model_id = model_id[0]
                        #Check if field already exists
                        referential_id = context.get('referential_id',False)
                        field_ids = self.pool.get('ir.model.fields').search(cr, uid, [('name', '=', field_name), ('model_id', '=', model_id)])
                        field_vals = {
                            'name':field_name,
                            'model_id':model_id,
                            'model':model_name,
                            'field_description':vals.get('frontend_label', False) or vals['attribute_code'],
                            'ttype':self._type_conversion[vals.get('frontend_input', False)],
                            'translate': self._is_attribute_translatable(vals),
                        }
                        if not vals['attribute_code'] in self._not_store_in_json:
                            if model_name == 'product.template':
                                field_vals['serialization_field_id'] = self.pool.get('ir.model.fields').search(cr, uid, [('name', '=', 'magerp_tmpl'), ('model', '=', 'product.template')], context=context)[0]
                            else:
                                field_vals['serialization_field_id'] = self.pool.get('ir.model.fields').search(cr, uid, [('name', '=', 'magerp_variant'), ('model', '=', 'product.product')], context=context)[0]
                        if not field_ids:
                            #The field is not there create it
                            #IF char add size
                            if field_vals['ttype'] == 'char':
                                field_vals['size'] = 100
                            if field_vals['ttype'] == 'many2one':
                                field_vals['relation'] = 'magerp.product_attribute_options'
                                field_vals['domain'] = "[('attribute_id','='," + str(crid) + ")]"
                            if field_vals['ttype'] == 'many2many':
                                field_vals['relation'] = 'magerp.product_attribute_options'
                                field_vals['domain'] = "[('attribute_id','='," + str(crid) + ")]"
                            field_vals['state'] = 'manual'
                            #All field values are computed, now save
                            field_id = self.pool.get('ir.model.fields').create(cr, uid, field_vals)
                            # mapping have to be based on product.product
                            model_id = self.pool.get('ir.model').search(cr, uid, [('model', '=', 'product.product')])[0]
                            self._create_mapping(cr, uid, field_vals['ttype'], field_id, field_name, referential_id, model_id, vals, crid)
        return crid

    def _default_mapping(self, cr, uid, ttype, field_name, vals, attribute_id, model_id, mapping_line, referential_id):
        #TODO refactor me and use the direct mapping
        #If the field have restriction on domain
        #Maybe we can give the posibility to map directly m2m and m2o field_description
        #by filtrering directly with the domain and the string value
        if ttype in ['char', 'text', 'date', 'float', 'weee', 'boolean']:
            mapping_line['evaluation_type'] = 'direct'
            if ttype == 'float':
                mapping_line['external_type'] = 'float'
            elif ttype == 'boolean':
                mapping_line['external_type'] = 'int'
            else:
                mapping_line['external_type'] = 'unicode'

        elif ttype in ['many2one']:
            mapping_line['evaluation_type'] = 'function'
            mapping_line['in_function'] = \
               ("if '%(attribute_code)s' in resource:\n"
                "    option_id = self.pool.get('magerp.product_attribute_options').search(cr, uid, [('attribute_id','=',%(attribute_id)s),('value','=',ifield)])\n"
                "    if option_id:\n"
                "        result = [('%(field_name)s', option_id[0])]")  % ({'attribute_code': vals['attribute_code'], 'attribute_id': attribute_id, 'field_name': field_name})
            # we browse on resource['%(field_name)s'][0] because resource[field_name] is in the form (id, name)
            mapping_line['out_function'] = \
               ("if '%(field_name)s' in resource:\n"
                "    result = [('%(attribute_code)s', False)]\n"
                "    if resource.get('%(field_name)s'):\n"
                "        option = self.pool.get('magerp.product_attribute_options').browse(cr, uid, resource['%(field_name)s'][0])\n"
                "        if option:\n"
                "            result = [('%(attribute_code)s', option.value)]") % ({'field_name': field_name, 'attribute_code': vals['attribute_code']})
        elif ttype in ['many2many']:
            mapping_line['evaluation_type'] = 'function'
            mapping_line['in_function'] = ("option_ids = []\n"
                "opt_obj = self.pool.get('magerp.product_attribute_options')\n"
                "for ext_option_id in ifield:\n"
                "    option_ids.extend(opt_obj.search(cr, uid, [('attribute_id','=',%(attribute_id)s), ('value','=',ext_option_id)]))\n"
                "result = [('%(field_name)s', [(6, 0, option_ids)])]") % ({'attribute_id': attribute_id, 'field_name': field_name})
            mapping_line['out_function'] = ("result=[('%(attribute_code)s', [])]\n"
                "if resource.get('%(field_name)s'):\n"
                "    options = self.pool.get('magerp.product_attribute_options').browse(cr, uid, resource['%(field_name)s'])\n"
                "    result = [('%(attribute_code)s', [option.value for option in options])]") % \
               ({'field_name': field_name, 'attribute_code': vals['attribute_code']})
        elif ttype in ['binary']:
            warning_text = "Binary mapping is actually not supported (attribute: %s)" % (vals['attribute_code'],)
            _logger.warn(warning_text)
            warning_msg = ("import logging\n"
                           "logger = logging.getLogger('in/out_function')\n"
                           "logger.warn('%s')") % (warning_text,)
            mapping_line['in_function'] = mapping_line['out_function'] = warning_msg
        return mapping_line

    def _create_mapping(self, cr, uid, ttype, field_id, field_name, referential_id, model_id, vals, attribute_id):
        """Search & create mapping entries"""
        if vals['attribute_code'] in self._no_create_list:
            return False
        mapping_id = self.pool.get('external.mapping').search(cr, uid, [('referential_id', '=', referential_id), ('model_id', '=', model_id)])
        if mapping_id:
            existing_line = self.pool.get('external.mapping.line').search(cr, uid, [('external_field', '=', vals['attribute_code']), ('mapping_id', '=', mapping_id[0])])
            if not existing_line:
                mapping_line = {'external_field': vals['attribute_code'],
                                'sequence': 0,
                                'mapping_id': mapping_id[0],
                                'type': self._sync_way.get(vals['attribute_code'], 'in_out'),
                                'external_type': self._type_casts[vals.get('frontend_input', False)],
                                'field_id': field_id, }
                mapping_line = self._default_mapping(cr, uid, ttype, field_name, vals, attribute_id, model_id, mapping_line, referential_id)
                self.pool.get('external.mapping.line').create(cr, uid, mapping_line)
        return True


"""Dont remove the code, we might need it --sharoon
class magerp_product_attributes_set_info(Model):
    _name="magerp.product_attributes.set_info"
    _description = "Attribute Set information for each attribute"
    _columns = {
        'referential_id':fields.many2one('external.referential', 'Magento Instance', readonly=True),
        'attribute_set_id':
        'sort':fields.integer('sort')
        'group_sort':fields.integer('group_sort')
        'group_id':
                }
magerp_product_attributes_set_info()"""

class magerp_product_attribute_options(MagerpModel):
    _name = "magerp.product_attribute_options"
    _description = "Options  of selected attributes"
    _rec_name = "label"

    _columns = {
        'attribute_id':fields.many2one('magerp.product_attributes', 'Attribute'),
        'attribute_name':fields.related('attribute_id', 'attribute_code', type='char', string='Attribute Code',),
        'value':fields.char('Value', size=200),
        'ipcast':fields.char('Type cast', size=50),
        'label':fields.char('Label', size=100),
        'referential_id':fields.many2one('external.referential', 'Magento Instance', readonly=True),
    }


    def data_to_save(self, cr, uid, vals_list, update=False, context=None):
        """This method will take data from vals and use context to create record"""
        if context is None:
            context = {}
        to_remove_ids = []
        if update:
            to_remove_ids = self.search(cr, uid, [('attribute_id', '=', context['attribute_id'])])

        for vals in vals_list:
            if vals.get('value', False) and vals.get('label', False):
                value = unicode(vals['value'])
                #Fixme: What to do when Magento offers emty options which open erp doesnt?
                #Such cases dictionary is: {'value':'','label':''}
                if update:
                    existing_ids = self.search(
                        cr, uid,
                        [('attribute_id', '=', context['attribute_id']),
                         ('value', '=', value)],
                        context=context)
                    if len(existing_ids) == 1:
                        to_remove_ids.remove(existing_ids[0])
                        self.write(cr, uid, existing_ids[0], {'label': vals.get('label', False)})
                        continue

                self.create(cr, uid, {
                                        'attribute_id': context['attribute_id'],
                                        'value': value,
                                        'label': vals['label'],
                                        'referential_id': context['referential_id'],
                                    }
                            )

        self.unlink(cr, uid, to_remove_ids) #if a product points to a removed option, it will get no option instead

    def get_option_id(self, cr, uid, attr_name, value, instance):
        attr_id = self.search(cr, uid, [('attribute_name', '=', attr_name), ('value', '=', value), ('referential_id', '=', instance)])
        if attr_id:
            return attr_id[0]
        else:
            return False


class magerp_product_attribute_set(MagerpModel):
    _name = "magerp.product_attribute_set"
    _description = "Attribute sets in products"
    _rec_name = 'attribute_set_name'

    _columns = {
        'sort_order':fields.integer('Sort Order'),
        'attribute_set_name':fields.char('Set Name', size=100),
        'attributes':fields.many2many('magerp.product_attributes', 'magerp_attrset_attr_rel', 'set_id', 'attr_id', 'Attributes'),
        'referential_id':fields.many2one('external.referential', 'Magento Instance', readonly=True),
        'magento_id':fields.integer('Magento ID'),
        }


    def update_attribute(self, cr, uid, ids, context=None):
        ref_obj = self.pool.get('external.referential')
        mag_ref_ids = ref_obj.search(cr, uid, [('version_id','ilike', 'magento')], context=context)
        for referential in ref_obj.browse(cr, uid, mag_ref_ids, context=context):
            external_session = ExternalSession(referential, referential)
            for attr_set_id in ids:
                attr_set_ext_id = self.get_extid(cr, uid, attr_set_id, referential.id, context=context)
                if attr_set_ext_id:
                    self._import_attribute(cr, uid, external_session, attr_set_ext_id, context=context)
                    self._import_attribute_relation(cr, uid, external_session, [attr_set_ext_id], context=context)
        return True

    #TODO refactor me
    def _import_attribute(self, cr, uid, external_session, attr_set_ext_id, attributes_imported=None, context=None):
        attr_obj = self.pool.get('magerp.product_attributes')
        mage_inp = external_session.connection.call('ol_catalog_product_attribute.list', [attr_set_ext_id])             #Get the tree
        mapping = {'magerp.product_attributes' : attr_obj._get_mapping(cr, uid, external_session.referential_id.id, context=context)}
        attribut_to_import = []
        if not attributes_imported: attributes_imported=[]
        for attribut in mage_inp:
            ext_id = attribut['attribute_id']
            if not ext_id in attributes_imported:
                attributes_imported.append(ext_id)
                attr_obj._record_one_external_resource(cr, uid, external_session, attribut,
                                                defaults={'referential_id':external_session.referential_id.id},
                                                mapping=mapping,
                                                context=context,
                                            )
        external_session.logger.info("All attributs for the attributs set id %s was succesfully imported", attr_set_ext_id)
        return True

    #TODO refactor me
    def _import_attribute_relation(self, cr, uid, external_session, attr_set_ext_ids, context=None):
        #Relate attribute sets & attributes
        mage_inp = {}
        #Pass in {attribute_set_id:{attributes},attribute_set_id2:{attributes}}
        #print "Attribute sets are:", attrib_sets
        #TODO find a solution in order to import the relation in a incremental way (maybe splitting this function in two)
        for attr_id in attr_set_ext_ids:
            mage_inp[attr_id] = external_session.connection.call('ol_catalog_product_attribute.relations', [attr_id])
        if mage_inp:
            self.relate(cr, uid, mage_inp, external_session.referential_id.id, context)
        return True

    def relate(self, cr, uid, mage_inp, instance, *args):
        #TODO: Build the relations code
        #Note: It is better to insert multiple record by cr.execute because:
        #1. Everything ends in a sinlge query (Fast)
        #2. If the values are updated using the return value for m2m field it may execute much slower
        #3. Multirow insert is 4x faster than reduntant insert ref:http://kaiv.wordpress.com/2007/07/19/faster-insert-for-multiple-rows/
        rel_dict = {}
        #Get all attributes in onew place to convert from mage_id to oe_id
        attr_ids = self.pool.get('magerp.product_attributes').search(cr, uid, [])
        attr_list_oe = self.pool.get('magerp.product_attributes').read(cr, uid, attr_ids, ['magento_id'])
        attr_list = {}
        for each_set in attr_list_oe:
            attr_list[each_set['magento_id']] = each_set['id']
        attr_set_ids = self.search(cr, uid, [])
        attr_set_list_oe = self.read(cr, uid, attr_set_ids, ['magento_id'])
        attr_set_list = {}
        #print attr_set_list_oe
        for each_set in attr_set_list_oe:
            attr_set_list[each_set['magento_id']] = each_set['id']
        key_attrs = []
        #print mage_inp
        for each_key in mage_inp.keys():
            self.write(cr, uid, attr_set_list[each_key], {'attributes': [[6, 0, []]]})
            for each_attr in mage_inp[each_key]:
                if each_attr['attribute_id']:
                    try:
                        key_attrs.append((attr_set_list[each_key], attr_list[int(each_attr['attribute_id'])]))
                    except Exception, e:
                        pass
        #rel_dict {set_id:[attr_id_1,attr_id_2,],set_id2:[attr_id_1,attr_id_3]}
        if len(key_attrs) > 0:
            #rel_dict {set_id:[attr_id_1,attr_id_2,],set_id2:[attr_id_1,attr_id_3]}
            query = "INSERT INTO magerp_attrset_attr_rel (set_id,attr_id) VALUES "
            for each_pair in key_attrs:
                query += str(each_pair)
                query += ","
            query = query[0:len(query) - 1] + ";"
            cr.execute(query)
        return True


class magerp_product_attribute_groups(MagerpModel):
    _name = "magerp.product_attribute_groups"
    _description = "Attribute groups in Magento"
    _rec_name = 'attribute_group_name'
    _order = "sort_order"
    def _get_set(self, cr, uid, ids, prop, unknow_none, context=None):
        res = {}
        for attribute_group in self.browse(cr, uid, ids, context):
            res[attribute_group.id] = self.pool.get('magerp.product_attribute_set').extid_to_oeid(cr, uid, attribute_group.attribute_set_id, attribute_group.referential_id.id)
        return res

    # XXX a deplacer dans MagentoConnector
    def _get_filter(self, cr, uid, external_session, step, previous_filter=None, context=None):
        attrset_ids = self.pool.get('magerp.product_attribute_set').get_all_extid_from_referential(cr, uid, external_session.referential_id.id, context=context)
        return {'attribute_set_id':{'in':attrset_ids}}

    _columns = {
        'attribute_set_id':fields.integer('Attribute Set ID'),
        'attribute_set':fields.function(_get_set, type="many2one", relation="magerp.product_attribute_set", method=True, string="Attribute Set"),
        'attribute_group_name':fields.char('Group Name', size=100),
        'sort_order':fields.integer('Sort Order'),
        'default_id':fields.integer('Default'),
        'referential_id':fields.many2one('external.referential', 'Magento Instance', readonly=True),
        }

class product_tierprice(Model):
    _name = "product.tierprice"
    _description = "Implements magento tier pricing"

    _columns = {
        'web_scope':fields.selection([
            ('all', 'All Websites'),
            ('specific', 'Specific Website'),
        ], 'Scope'),
        'website_id':fields.many2one('external.shop.group', 'Website'),
        'group_scope':fields.selection([
            ('1', 'All groups'),
            ('0', 'Specific group')
        ]),
        'cust_group':fields.many2one('res.partner.category', 'Customer Group'),
        'website_price':fields.float('Website Price', digits=(10, 2),),
        'price':fields.float('Price', digits=(10, 2),),
        'price_qty':fields.float('Quantity Slab', digits=(10, 4), help="Slab & above eg.For 10 and above enter 10"),
        'product':fields.many2one('product.product', 'Product'),
        'referential_id':fields.many2one('external.referential', 'Magento Instance', readonly=True),
        }
    _mapping = {
        'cust_group':(False, int, """result=self.pool.get('res.partner.category').mage_to_oe(cr,uid,cust_group,instance)\nif result:\n\tresult=[('cust_group',result[0])]\nelse:\n\tresult=[('cust_group',False)]"""),
        'all_groups':(False, str, """if all_groups=='1':\n\tresult=[('group_scope','1')]\nelse:\n\tresult=[('group_scope','1')]"""),
        'website_price':('website_price', float),
        'price':('price', float),
        'website_id':(False, int, """result=self.pool.get('external.shop.group').mage_to_oe(cr,uid,website_id,instance)\nif result:\n\tresult=[('website_id',result[0])]\nelse:\n\tresult=[('website_id',False)]"""),
        'price_qty':('price_qty', float),
        }

class product_product_type(Model):
    _name = 'magerp.product_product_type'
    _columns = {
        'name': fields.char('Name', size=100, required=True, translate=True),
        'product_type': fields.char('Type', size=100, required=True, help="Use the same name of Magento product type, for example 'simple'."),
        'default_type': fields.selection([('product','Stockable Product'),('consu', 'Consumable'),('service','Service')], 'Default Product Type', required=True, help="Default product's type (Procurement) when a product is imported from Magento."),
        }


class product_mag_osv(MagerpModel):
    _register = False # Set to false if the model shouldn't be automatically discovered.

    #remember one thing in life: Magento lies: it tells attributes are required while they are awkward to fill
    #and will have a nice default vaule anyway, that's why we avoid making them mandatory in the product view
    _magento_fake_mandatory_attrs = ['created_at', 'updated_at', 'has_options', 'required_options', 'model']

    def open_magento_fields(self, cr, uid, ids, context=None):
        ir_model_data_obj = self.pool.get('ir.model.data')
        ir_model_data_id = ir_model_data_obj.search(cr, uid, [['model', '=', 'ir.ui.view'], ['name', '=', self._name.replace('.','_') + '_wizard_form_view_magerpdynamic']], context=context)
        if ir_model_data_id:
            res_id = ir_model_data_obj.read(cr, uid, ir_model_data_id, fields=['res_id'])[0]['res_id']
        set_id = self.read(cr, uid, ids, fields=['set'], context=context)[0]['set']

        if not set_id:
            raise except_osv(_('User Error'), _('Please chose an attribute set before'))

        return {
            'name': 'Magento Fields',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': [res_id],
            'res_model': self._name,
            'context': "{'set': %s, 'open_from_button_object_id': %s}"%(set_id[0], ids),
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'res_id': ids and ids[0] or False,
        }

    def save_and_close_magento_fields(self, cr, uid, ids, context=None):
        '''this empty function will save the magento field'''
        return {'type': 'ir.actions.act_window_close'}

    def redefine_prod_view(self, cr, uid, field_names, context=None):
        """
        Rebuild the product view with attribute groups and attributes
        """
        if context is None: context = {}
        attr_set_obj = self.pool.get('magerp.product_attribute_set')
        attr_group_obj = self.pool.get('magerp.product_attribute_groups')
        attr_obj = self.pool.get('magerp.product_attributes')
        translation_obj = self.pool.get('ir.translation')

        attribute_set_id = context['set']
        attr_set = attr_set_obj.browse(cr, uid, attribute_set_id)
        attr_group_fields_rel = {}

        multiwebsites = context.get('multiwebsite', False)

        fields_get = self.fields_get(cr, uid, field_names, context)

        cr.execute("select attr_id, group_id, attribute_code, frontend_input, "
                   "frontend_label, is_required, apply_to, field_name "
                   "from magerp_attrset_attr_rel "
                   "left join magerp_product_attributes "
                   "on magerp_product_attributes.id = attr_id "
                   "where magerp_attrset_attr_rel.set_id=%s" %
                   attribute_set_id)

        results = cr.dictfetchall()
        attribute = results.pop()
        while results:
            mag_group_id = attribute['group_id']
            oerp_group_id = attr_group_obj.extid_to_existing_oeid(
                cr, uid, attr_set.referential_id.id, mag_group_id)
            # FIXME: workaround in multi-Magento instances (databases)
            # where attribute group might not be found due to the way we
            # share attributes currently
            if not oerp_group_id:
                ref_ids = self.pool.get(
                    'external.referential').search(cr, uid, [])
                for ref_id in ref_ids:
                     if ref_id != attr_set.referential_id.id:
                         oerp_group_id = attr_group_obj.extid_to_existing_oeid(
                             cr, uid, ref_id, mag_group_id)
                         if oerp_group_id:
                             break

            group_name = attr_group_obj.read(
                cr, uid, oerp_group_id,
                ['attribute_group_name'],
                context=context)['attribute_group_name']

            # Create a page for each attribute group
            attr_group_fields_rel.setdefault(group_name, [])
            while True:
                if attribute['group_id'] != mag_group_id:
                    break

                if attribute['field_name'] in field_names:
                    if not attribute['attribute_code'] in attr_obj._no_create_list:
                        if (group_name in  ['Meta Information',
                                            'General',
                                            'Custom Layout Update',
                                            'Prices',
                                            'Design']) or \
                           GROUP_CUSTOM_ATTRS_TOGETHER==False:
                            attr_group_fields_rel[group_name].append(attribute)
                        else:
                            attr_group_fields_rel.setdefault(
                                'Custom Attributes', []).append(attribute)
                if results:
                    attribute = results.pop()
                else:
                    break

        notebook = etree.Element('notebook', colspan="4")

        attribute_groups = attr_group_fields_rel.keys()
        attribute_groups.sort()
        for group in attribute_groups:
            lang = context.get('lang', '')
            trans = translation_obj._get_source(
                cr, uid, 'product.product', 'view', lang, group)
            trans = trans or group
            if attr_group_fields_rel.get(group):
                page = etree.SubElement(notebook, 'page', string=trans)
                for attribute in attr_group_fields_rel.get(group, []):
                    if attribute['frontend_input'] == 'textarea':
                        etree.SubElement(page, 'newline')
                        etree.SubElement(
                            page,
                            'separator',
                            colspan="4",
                            string=fields_get[attribute['field_name']]['string'])

                    f = etree.SubElement(
                        page, 'field', name=attribute['field_name'])

                    # apply_to is a string like
                    # "simple,configurable,virtual,bundle,downloadable"
                    req_apply_to = not attribute['apply_to'] or \
                        'simple' in attribute['apply_to'] or \
                        'configurable' in attribute['apply_to']
                    if attribute['is_required'] and \
                       req_apply_to and \
                        attribute['attribute_code'] not in self._magento_fake_mandatory_attrs:
                        f.set('attrs', "{'required': [('magento_exportable', '=', True)]}")

                    if attribute['frontend_input'] == 'textarea':
                        f.set('nolabel', "1")
                        f.set('colspan', "4")

                    setup_modifiers(f, fields_get[attribute['field_name']],
                                    context=context)

        if multiwebsites:
            website_page = etree.SubElement(
                notebook, 'page', string=_('Websites'))
            wf = etree.SubElement(
                website_page, 'field', name='websites_ids', nolabel="1")
            setup_modifiers(wf, fields_get['websites_ids'], context=context)

        return notebook

    def _filter_fields_to_return(self, cr, uid, field_names, context=None):
        '''This function is a hook in order to filter the fields that appears on the view'''
        return field_names

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if context is None:
            context = {}
        result = super(product_mag_osv, self).fields_view_get(
            cr, uid, view_id,view_type,context,toolbar=toolbar)
        if view_type == 'form':
            eview = etree.fromstring(result['arch'])
            btn = eview.xpath("//button[@name='open_magento_fields']")
            if btn:
                btn = btn[0]
            page_placeholder = eview.xpath(
                "//page[@string='attributes_placeholder']")

            attrs_mag_notebook = "{'invisible': [('set', '=', False)]}"

            if context.get('set'):
                fields_obj = self.pool.get('ir.model.fields')
                models = ['product.template']
                if self._name == 'product.product':
                    models.append('product.product')

                model_ids = self.pool.get('ir.model').search(
                    cr, uid, [('model', 'in', models)], context=context)
                field_ids = fields_obj.search(
                    cr, uid,
                    [('model_id', 'in', model_ids)],
                    context=context)
                #TODO it will be better to avoid adding fields here
                #Moreover we should also add the field mag_manage_stock
                field_names = ['product_type']
                fields = fields_obj.browse(cr, uid, field_ids, context=context)
                for field in fields:
                    if field.name.startswith('x_'):
                        field_names.append(field.name)
                website_ids = self.pool.get('external.shop.group').search(
                    cr, uid,
                    [('referential_type', '=ilike', 'mag%')],
                    context=context)
                if len(website_ids) > 1:
                    context['multiwebsite'] = True
                    field_names.append('websites_ids')

                field_names = self._filter_fields_to_return(
                    cr, uid, field_names, context)
                result['fields'].update(
                    self.fields_get(cr, uid, field_names, context))

                attributes_notebook = self.redefine_prod_view(
                                    cr, uid, field_names, context)

                # if the placeholder is a "page", that means we are
                # in the product main form. If it is a "separator", it
                # means we are in the attributes popup
                if page_placeholder:
                    placeholder = page_placeholder[0]
                    magento_page = etree.Element(
                        'page',
                        string=_('Magento Information'),
                        attrs=attrs_mag_notebook)
                    setup_modifiers(magento_page, context=context)
                    f = etree.SubElement(
                        magento_page,
                        'field',
                        name='product_type',
                        attrs="{'required': [('magento_exportable', '=', True)]}")
                    setup_modifiers(f, field=result['fields']['product_type'], context=context)
                    magento_page.append(attributes_notebook)
                    btn.getparent().remove(btn)
                else:
                    placeholder = eview.xpath(
                        "//separator[@string='attributes_placeholder']")[0]
                    magento_page = attributes_notebook

                placeholder.getparent().replace(placeholder, magento_page)
            elif btn != []:
                new_btn = etree.Element(
                    'button',
                    name='open_magento_fields',
                    string=_('Open Magento Fields'),
                    icon='gtk-go-forward',
                    type='object',
                    colspan='2',
                    attrs=attrs_mag_notebook)
                setup_modifiers(new_btn, context=context)
                btn.getparent().replace(btn, new_btn)
                if page_placeholder:
                    placeholder = page_placeholder[0]
                    placeholder.getparent().remove(placeholder)

            result['arch'] = etree.tostring(eview, pretty_print=True)
            #TODO understand (and fix) why the orm fill the field size for the text field :S
            for field in result['fields']:
                if result['fields'][field]['type'] == 'text':
                    if 'size' in result['fields'][field]: del result['fields'][field]['size']
        return result

class product_template(product_mag_osv):
    _inherit = "product.template"
    _columns = {
        'magerp_tmpl' : fields.serialized('Magento Template Fields'),
        'set':fields.many2one('magerp.product_attribute_set', 'Attribute Set'),
        'websites_ids': fields.many2many('external.shop.group', 'magerp_product_shop_group_rel', 'product_id', 'shop_group_id', 'Websites', help='By defaut product will be exported on every website, if you want to export it only on some website select them here'),
        'mag_manage_stock': fields.selection([
                                ('use_default','Use Default Config'),
                                ('no', 'Do Not Manage Stock'),
                                ('yes','Manage Stock')],
                                'Manage Stock Level'),
        'mag_manage_stock_shortage': fields.selection([
                                ('use_default','Use Default Config'),
                                ('no', 'No Sell'),
                                ('yes','Sell qty < 0'),
                                ('yes-and-notification','Sell qty < 0 and Use Customer Notification')],
                                'Manage Inventory Shortage'),
        }

    _defaults = {
        'mag_manage_stock': 'use_default',
        'mag_manage_stock_shortage': 'use_default',
        }


class product_product(orm.Model):
    _inherit = 'product.product'

    def write(self, cr, uid, ids, vals, context=None):
        if vals.get('referential_id', False):
            instance = vals['referential_id']
            #Filter the keys to be changes
            if ids:
                if type(ids) == list and len(ids) == 1:
                    ids = ids[0]
                elif type(ids) == int or type(ids) == long:
                    ids = ids
                else:
                    return False
            tier_price = False
            if 'x_magerp_tier_price' in vals.keys():
                tier_price = vals.pop('x_magerp_tier_price')
            tp_obj = self.pool.get('product.tierprice')
            #Delete existing tier prices
            tier_price_ids = tp_obj.search(cr, uid, [('product', '=', ids)])
            if tier_price_ids:
                tp_obj.unlink(cr, uid, tier_price_ids)
            #Save the tier price
            if tier_price:
                self.create_tier_price(cr, uid, tier_price, instance, ids)
        stat = super(product_product, self).write(cr, uid, ids, vals, context)
        #Perform other operation
        return stat

    def create_tier_price(self, cr, uid, tier_price, instance, product_id):
        tp_obj = self.pool.get('product.tierprice')
        for each in eval(tier_price):
            tier_vals = {}
            cust_group = self.pool.get('res.partner.category').mage_to_oe(cr, uid, int(each['cust_group']), instance)
            if cust_group:
                tier_vals['cust_group'] = cust_group[0]
            else:
                tier_vals['cust_group'] = False
            tier_vals['website_price'] = float(each['website_price'])
            tier_vals['price'] = float(each['price'])
            tier_vals['price_qty'] = float(each['price_qty'])
            tier_vals['product'] = product_id
            tier_vals['referential_id'] = instance
            tier_vals['group_scope'] = each['all_groups']
            if each['website_id'] == '0':
                tier_vals['web_scope'] = 'all'
            else:
                tier_vals['web_scope'] = 'specific'
                tier_vals['website_id'] = self.pool.get('external.shop.group').mage_to_oe(cr, uid, int(each['website_id']), instance)
            tp_obj.create(cr, uid, tier_vals)

    def create(self, cr, uid, vals, context=None):
        tier_price = False
        if vals.get('referential_id', False):
            instance = vals['referential_id']
            #Filter keys to be changed
            if 'x_magerp_tier_price' in vals.keys():
                tier_price = vals.pop('x_magerp_tier_price')

        crid = super(product_product, self).create(cr, uid, vals, context)
        #Save the tier price
        if tier_price:
            self.create_tier_price(cr, uid, tier_price, instance, crid)
        #Perform other operations
        return crid

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}

        default['magento_exportable'] = False

        return super(product_product, self).copy(cr, uid, id, default=default, context=context)

    def unlink(self, cr, uid, ids, context=None):
        #if product is mapped to magento, not delete it
        not_delete = False
        sale_obj = self.pool.get('sale.shop')
        search_params = [
            ('magento_shop', '=', True),
        ]
        shops_ids = sale_obj.search(cr, uid, search_params)

        for shop in sale_obj.browse(cr, uid, shops_ids, context):
            if shop.referential_id and shop.referential_id.type_id.name == 'Magento':
                for product_id in ids:
                    mgn_product = self.get_extid(cr, uid, product_id, shop.referential_id.id)
                    if mgn_product:
                        not_delete = True
                        break
        if not_delete:
            if len(ids) > 1:
                raise except_osv(_('Warning!'),
                                 _('They are some products related to Magento. '
                                   'They can not be deleted!\n'
                                   'You can change their Magento status to "Disabled" '
                                   'and uncheck the active box to hide them from OpenERP.'))
            else:
                raise except_osv(_('Warning!'),
                                 _('This product is related to Magento. '
                                   'It can not be deleted!\n'
                                   'You can change it Magento status to "Disabled" '
                                   'and uncheck the active box to hide it from OpenERP.'))
        else:
            return super(product_product, self).unlink(cr, uid, ids, context)

    def _prepare_inventory_magento_vals(self, cr, uid, product, stock, shop,
                                        context=None):
        """
        Prepare the values to send to Magento (message product_stock.update).
        Can be inherited to customize the values to send.

        :param browse_record product: browseable product
        :param browse_record stock: browseable stock location
        :param browse_record shop: browseable shop
        :return: a dict of values which will be sent to Magento with a call to:
        product_stock.update
        """
        map_shortage = {
            "use_default": 0,
            "no": 0,
            "yes": 1,
            "yes-and-notification": 2,
        }

        stock_field = (shop.product_stock_field_id and
                       shop.product_stock_field_id.name or
                       'virtual_available')
        stock_quantity = product[stock_field]

        return {'qty': stock_quantity,
                'manage_stock': int(product.mag_manage_stock == 'yes'),
                'use_config_manage_stock': int(product.mag_manage_stock == 'use_default'),
                'backorders': map_shortage[product.mag_manage_stock_shortage],
                'use_config_backorders':int(product.mag_manage_stock_shortage == 'use_default'),
                # put the stock availability to "out of stock"
                'is_in_stock': int(stock_quantity > 0)}

    def export_inventory(self, cr, uid, external_session, ids, context=None):
        """
        Export to Magento the stock quantity for the products in ids which
        are already exported on Magento and are not service products.

        :param int shop_id: id of the shop where the stock inventory has
        to be exported
        :param Connection connection: connection object
        :return: True
        """
        #TODO get also the list of product which the option mag_manage_stock have changed
        #This can be base on the group_fields that can try tle last write date of a group of fields
        if context is None: context = {}

        # use the stock location defined on the sale shop
        # to compute the stock value
        stock = external_session.sync_from_object.warehouse_id.lot_stock_id
        location_ctx = context.copy()
        location_ctx['location'] = stock.id
        for product_id in ids:
            self._export_inventory(cr, uid, external_session, product_id, context=location_ctx)

        return True

    @catch_error_in_report
    def _export_inventory(self, cr, uid, external_session, product_id, context=None):
        product = self.browse(cr, uid, product_id, context=context)
        stock = external_session.sync_from_object.warehouse_id.lot_stock_id
        mag_product_id = self.get_extid(
            cr, uid, product.id, external_session.referential_id.id, context=context)
        if not mag_product_id:
            return False  # skip products which are not exported
        inventory_vals = self._prepare_inventory_magento_vals(
            cr, uid, product, stock, external_session.sync_from_object, context=context)

        external_session.connection.call('oerp_cataloginventory_stock_item.update',
                        [mag_product_id, inventory_vals])

        external_session.logger.info(
            "Successfully updated stock level at %s for "
            "product with code %s " %
            (inventory_vals['qty'], product.default_code))
        return True

    #TODO change the magento api to be able to change the link direct from the function
    # ol_catalog_product.update
    def ext_update_link_data(self, cr, uid, external_session, resources, mapping=None, mapping_id=None, context=None):
        for resource_id, resource in resources.items():
            for type_selection in self.pool.get('product.link').get_link_type_selection(cr, uid, context):
                link_type = type_selection[0]
                position = {}
                linked_product_ids = []
                for link in resource[context['main_lang']].get('product_link', []):
                    if link['type'] == link_type:
                        if link['is_active']:
                            linked_product_ids.append(link['link_product_id'])
                            position[link['link_product_id']] = link['position']
                self.ext_product_assign(cr, uid, external_session, link_type, resource[context['main_lang']]['ext_id'],
                                            linked_product_ids, position=position, context=context)
        return True

    def ext_product_assign(self, cr, uid, external_session, link_type, ext_parent_id, ext_child_ids,
                                                    quantities=None, position=None, context=None):
        context = context or {}
        position = position or {}
        quantities = quantities or {}


        #Patch for magento api prototype
        #for now the method for goodies is freeproduct
        #It will be renammed soon and so this patch will be remove too
        if link_type == 'goodies': link_type= 'freeproduct'
        #END PATCH

        magento_args = [link_type, ext_parent_id]
        # magento existing children ids
        child_list = external_session.connection.call('product_link.list', magento_args)
        old_child_ext_ids = [x['product_id'] for x in child_list]

        ext_id_to_remove = []
        ext_id_to_assign = []
        ext_id_to_update = []

        # compute the diff between openerp and magento
        for c_ext_id in old_child_ext_ids:
            if c_ext_id not in ext_child_ids:
                ext_id_to_remove.append(c_ext_id)
        for c_ext_id in ext_child_ids:
            if c_ext_id in old_child_ext_ids:
                ext_id_to_update.append(c_ext_id)
            else:
                ext_id_to_assign.append(c_ext_id)

        # calls to magento to delete, create or update the links
        for c_ext_id in ext_id_to_remove:
             # remove the product links that are no more setup on openerp
            external_session.connection.call('product_link.remove', magento_args + [c_ext_id])
            external_session.logger.info(("Successfully removed assignment of type %s for"
                                 "product %s to product %s") % (link_type, ext_parent_id, c_ext_id))
        for c_ext_id in ext_id_to_assign:
            # assign new product links
            external_session.connection.call('product_link.assign',
                      magento_args +
                      [c_ext_id,
                          {'position': position.get(c_ext_id, 0),
                           'qty': quantities.get(c_ext_id, 1)}])
            external_session.logger.info(("Successfully assigned product %s to product %s"
                                            "with type %s") %(link_type, ext_parent_id, c_ext_id))
        for child_ext_id in ext_id_to_update:
            # update products links already assigned
            external_session.connection.call('product_link.update',
                      magento_args +
                      [c_ext_id,
                          {'position': position.get(c_ext_id, 0),
                           'qty': quantities.get(c_ext_id, 1)}])
            external_session.logger.info(("Successfully updated assignment of type %s of"
                                 "product %s to product %s") %(link_type, ext_parent_id, c_ext_id))
        return True

    #TODO move this code (get exportable image) and also some code in product_image.py and sale.py in base_sale_multichannel or in a new module in order to be more generic
    def get_exportable_images(self, cr, uid, external_session, ids, context=None):
        shop = external_session.sync_from_object
        image_obj = self.pool.get('product.images')
        images_exportable_ids = image_obj.search(cr, uid, [('product_id', 'in', ids)], context=context)
        images_to_update_ids = image_obj.get_all_oeid_from_referential(cr, uid, external_session.referential_id.id, context=None)
        images_to_create = [x for x in images_exportable_ids if not x in images_to_update_ids]
        if shop.last_images_export_date:
            images_to_update_ids = image_obj.search(cr, uid, [('id', 'in', images_to_update_ids), '|', ('create_date', '>', shop.last_images_export_date), ('write_date', '>', shop.last_images_export_date)], context=context)
        return {'to_create' : images_to_create, 'to_update' : images_to_update_ids}

    def _mag_import_product_links_type(self, cr, uid, product, link_type, external_session, context=None):
        if context is None: context = {}
        conn = external_session.connection
        product_link_obj = self.pool.get('product.link')
        selection_link_types = product_link_obj.get_link_type_selection(cr, uid, context)
        mag_product_id = self.get_extid(
            cr, uid, product.id, external_session.referential_id.id, context=context)
        # This method could be completed to import grouped products too, you know, for Magento a product link is as
        # well a cross-sell, up-sell, related than the assignment between grouped products
        if link_type in [ltype[0] for ltype in selection_link_types]:
            product_links = []
            try:
                product_links = conn.call('product_link.list', [link_type, mag_product_id])
            except Exception, e:
                self.log(cr, uid, product.id, "Error when retrieving the list of links in Magento for product with reference %s and product id %s !" % (product.default_code, product.id,))
                conn.logger.debug("Error when retrieving the list of links in Magento for product with reference %s and product id %s !" % (product.magento_sku, product.id,))

            for product_link in product_links:
                linked_product_id = self.get_or_create_oeid(
                    cr, uid,
                    external_session,
                    product_link['product_id'],
                    context=context)
                link_data = {
                    'product_id': product.id,
                    'type': link_type,
                    'linked_product_id': linked_product_id,
                    'sequence': product_link['position'],
                }

                existing_link = product_link_obj.search(cr, uid,
                    [('product_id', '=', link_data['product_id']),
                     ('type', '=', link_data['type']),
                     ('linked_product_id', '=', link_data['linked_product_id'])
                    ], context=context)
                if existing_link:
                    product_link_obj.write(cr, uid, existing_link, link_data, context=context)
                else:
                    product_link_obj.create(cr, uid, link_data, context=context)
                conn.logger.info("Successfully imported product link of type %s on product %s to product %s" %(link_type, product.id, linked_product_id))
        return True

    def mag_import_product_links_types(self, cr, uid, ids, link_types, external_session, context=None):
        if isinstance(ids, (int, long)): ids = [ids]
        for product in self.browse(cr, uid, ids, context=context):
            for link_type in link_types:
                self._mag_import_product_links_type(cr, uid, product, link_type, external_session, context=context)
        return True

    def mag_import_product_links(self, cr, uid, ids, external_session, context=None):
        link_types = self.pool.get('external.referential').get_magento_product_link_types(cr, uid, external_session.referential_id.id, external_session.connection, context=context)
        local_cr = pooler.get_db(cr.dbname).cursor()
        try:
            for product_id in ids:
                self.mag_import_product_links_types(local_cr, uid, [product_id], link_types, external_session, context=context)
                local_cr.commit()
        finally:
            local_cr.close()
        return True


# transfered from product.py ###############################


class product_images(MagerpModel):
    _inherit = "product.images"
    _columns = {
        'base_image':fields.boolean('Base Image'),
        'small_image':fields.boolean('Small Image'),
        'thumbnail':fields.boolean('Thumbnail'),
        'exclude':fields.boolean('Exclude'),
        'position':fields.integer('Position'),
        'sync_status':fields.boolean('Sync Status', readonly=True),
        'create_date': fields.datetime('Created date', readonly=True),
        'write_date': fields.datetime('Updated date', readonly=True),
        }
    _defaults = {
        'sync_status':lambda * a: False,
        'base_image':lambda * a:True,
        'small_image':lambda * a:True,
        'thumbnail':lambda * a:True,
        'exclude':lambda * a:False
        }

    def get_changed_ids(self, cr, uid, start_date=False):
        proxy = self.pool.get('product.images')
        domain = start_date and ['|', ('create_date', '>', start_date), ('write_date', '>', start_date)] or []
        return proxy.search(cr, uid, domain)

    def del_image_name(self, cr, uid, id, context=None):
        if context is None: context = {}
        image_ext_name_obj = self.pool.get('product.images.external.name')
        name_id = image_ext_name_obj.search(cr, uid, [('image_id', '=', id), ('external_referential_id', '=', context['referential_id'])], context=context)
        if name_id:
            return image_ext_name_obj.unlink(cr, uid, name_id, context=context)
        return False



    @only_for_referential(ref_categ ='Multichannel Sale')
    def _get_last_exported_date(self, cr, uid, external_session, context=None):
        shop = external_session.sync_from_object
        return shop.last_images_export_date

    @only_for_referential(ref_categ ='Multichannel Sale')
    @commit_now
    def _set_last_exported_date(self, cr, uid, external_session, date, context=None):
        shop = external_session.sync_from_object
        return self.pool.get('sale.shop').write(cr, uid, shop.id, {'last_images_export_date': date}, context=context)



    def update_remote_images(self, cr, uid, external_session, ids, context=None):
        if context is None:
            context = {}

        ir_model_data_obj = self.pool.get('ir.model.data')

        def detect_types(image):
            types = []
            if image.small_image:
                types.append('small_image')
            if image.base_image:
                types.append('image')
            if image.thumbnail:
                types.append('thumbnail')
            return types

        #TODO update the image file
        def update_image(product_extid, image_name, image):
            result = external_session.connection.call('catalog_product_attribute_media.update',
                               [product_extid,
                                image_name,
                                {'label':image.name,
                                 'exclude':image.exclude,
                                 'types':detect_types(image),
                                }
                               ])
            return result
        list_image = []
        list_image = self.read(cr, uid, ids, ['write_date', 'create_date'], context=context)

        date_2_image={}
        image_2_date={}
        for image in list_image:
            if date_2_image.get(image['write_date'] or image['create_date'], False):
                done = False
                count = 0
                while not done:
                    count += 1
                    if not date_2_image.get((image['write_date'] or image['create_date']) + '-' + str(count), False):
                        date_2_image[(image['write_date'] or image['create_date']) + '-' + str(count)] = image['id']
                        done = True
            else:
                date_2_image[image['write_date'] or image['create_date']] = image['id']
            image_2_date[image['id']] = image['write_date'] or image['create_date']
        list_date = date_2_image.keys()
        list_date.sort()

        ids = [date_2_image[date] for date in list_date]

        while ids:
            product_images = self.browse_w_order(cr, uid, ids[:1000], context=context)
            for each in product_images:
                product_extid = each.product_id.get_extid(external_session.referential_id.id)
                if not product_extid:
                    external_session.logger.info("The product %s do not exist on magento" %(each.product_id.default_code))
                else:
                    need_to_be_created = True
                    ext_file_name = each.get_extid(external_session.referential_id.id)
                    if ext_file_name: #If update
                        try:
                            external_session.logger.info("Updating %s's image: %s" %(each.product_id.default_code, each.name))
                            result = update_image(product_extid, ext_file_name, each)
                            external_session.logger.info("%s's image updated with sucess: %s" %(each.product_id.default_code, each.name))
                            need_to_be_created = False
                        except Exception, e:
                            external_session.logger.error(_("Error in connecting:%s") % (e))
                            if not "Fault 103" in str(e):
                                external_session.logger.error(_("Unknow error stop export"))
                                raise
                            else:
                                #If the image was deleded in magento, the external name is automatically deleded before trying to re-create the image in magento
                                model_data_ids = ir_model_data_obj.search(cr, uid, [('model', '=', self._name), ('res_id', '=', each.id), ('referential_id', '=', external_session.referential_id.id)])
                                if model_data_ids and len(model_data_ids) > 0:
                                    ir_model_data_obj.unlink(cr, uid, model_data_ids, context=context)
                                external_session.logger.error(_("The image don't exist in magento, try to create it"))
                    if need_to_be_created:
                        if each.product_id.default_code:
                            pas_ok = True
                            suceed = False
                            external_session.logger.info("Sending %s's image: %s" %(each.product_id.default_code, each.name))
                            data = {
                                'file':{
                                    'name':each.name,
                                    'content': each.file,
                                    'mime': each.link and each.url and mimetypes.guess_type(each.url)[0] \
                                            or each.extention and mimetypes.guess_type(each.name + each.extention)[0] \
                                            or 'image/jpeg',
                                    }
                            }
                            result = external_session.connection.call('catalog_product_attribute_media.create', [product_extid, data, False, 'id'])

                            self.create_external_id_vals(cr, uid, each.id, result, external_session.referential_id.id, context=context)
                            result = update_image(product_extid, result, each)
                            external_session.logger.info("%s's image send with sucess: %s" %(each.product_id.default_code, each.name))


                if context.get('last_images_export_date') and image_2_date[each.id] > context['last_images_export_date']: #indeed if a product was created a long time ago and checked as exportable recently, the write date of the image can be far away in the past
                    self._set_last_exported_date(cr, uid, external_session, image_2_date[each.id], context=context)
                cr.commit()
            ids = ids[1000:]
            external_session.logger.info("still %s image to export" %len(ids))
        return True
