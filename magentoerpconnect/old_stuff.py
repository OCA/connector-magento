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

