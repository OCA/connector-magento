# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright 2013
#    Author: Guewen Baconnier - Camptocamp
#            Augustin Cisterne-Kaas - Elico-corp
#            David Béal - Akretion
#            Sébastien Beau - Akretion
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


from openerp.osv import fields, orm
#from openerp.tools.translate import _
from openerp.osv.osv import except_osv
from openerp.addons.connector.unit.mapper import (
    mapping,
    #changed_by,
    ImportMapper,
    ExportMapper,)
#from openerp.addons.connector.exception import MappingError
from openerp.addons.magentoerpconnect.backend import magento
from openerp.addons.magentoerpconnect.unit.backend_adapter import GenericAdapter
from openerp.addons.magentoerpconnect.unit.binder import MagentoModelBinder
from openerp.addons.magentoerpconnect.unit.delete_synchronizer import (
    MagentoDeleteSynchronizer)
from openerp.addons.magentoerpconnect.unit.export_synchronizer import (
    MagentoExporter)
from openerp.addons.magentoerpconnect.unit.import_synchronizer import (
    DelayedBatchImport,
    MagentoImportSynchronizer,)


@magento(replacing=MagentoModelBinder)
class MagentoAttributeBinder(MagentoModelBinder):
    _model_name = [
        'magento.product.attribute',
        'magento.attribute.option',
        'magento.attribute.set',
        ]


# Attribute Set
class AttributeSet(orm.Model):
    _inherit = 'attribute.set'

    _columns = {
        'magento_bind_ids': fields.one2many(
            'magento.attribute.set',
            'openerp_id',
            string='Magento Bindings',),
    }


class MagentoAttributeSet(orm.Model):
    _name = 'magento.attribute.set'
    _description = "Magento attribute set"
    _inherit = 'magento.binding'

    MISSING_ATTRIB_SET_TPL = """'Attribute set template' field
        must be define on the backend :
        Connectors > Magento >
        Backends > '%s'
    """

    _columns = {
        'openerp_id': fields.many2one(
            'attribute.set',
            string='Attribute set',
            ondelete='cascade'),
        'attribute_set_name': fields.char(
            'Name',
            size=64,
            required=True),
        'sort_order': fields.integer(
            'Sort order',
            readonly=True),
    }

    def name_get(self, cr, uid, ids, context=None):
        res = []
        for elm in self.read(cr, uid, ids, ['attribute_set_name'],
                             context=context):
            res.append((elm['id'], elm['attribute_set_name']))
        return res

    def create(self, cr, uid, vals, context=None):
        super(MagentoAttributeSet, self).create(
            cr, uid, vals, context=context)
        if 'backend_id' in vals:
            backend = self.pool['magento.backend'].read(
                cr, uid, [vals['backend_id']],
                ['attribute_set_tpl_id', 'name'], context=context)
            if backend[0]['attribute_set_tpl_id']:
                return vals
            else:
                raise except_osv(
                    "Error: setting missing on backend",
                    self.MISSING_ATTRIB_SET_TPL
                    % backend[0]['name'])
        return False

    def get_magento_template(self, cr, uid, ids, context=None):
        for attr_set in self.browse(cr, uid, ids, context=context):
            if attr_set.backend_id.attribute_set_tpl_id:
                magento_attr_set_id = [attr_set.backend_id.attribute_set_tpl_id.id]
                magento_attr_set = self.read(cr, uid, [magento_attr_set_id],
                                             ['magento_id'], context=context)[0]
            else:
                raise except_osv(
                    "Error: setting missing on backend",
                    self.MISSING_ATTRIB_SET_TPL
                    % attr_set.backend_id.name)

        return magento_attr_set['magento_id']

    _sql_constraints = [
        ('magento_uniq', 'unique(backend_id, openerp_id)',
         "An 'Attribute set' with the same ID on this Magento backend "
         "already exists")
    ]


@magento
class AttributeSetAdapter(GenericAdapter):
    _model_name = 'magento.attribute.set'
    _magento_default_model = 'product_attribute_set'
    _magento_model = 'ol_catalog_product_attributeset'

    def create(self, data):
        """ Create a record on the external system """
        #import pdb;pdb.set_trace()
        return self._call('%s.create' % self._magento_default_model,
                          [data['attribute_set_name'], data['skeletonSetId']])

    def delete(self, id):
        return self._call('%s.remove' % self._magento_default_model, [str(id)])

    def search(self, filters=None):
        """ Search records according and returns a list of ids
        :rtype: list
        """
        return self._call('%s.search' % self._magento_model, [])

    def read(self, id, storeview_id=None, attributes=None):
        """ Returns the information of a record
        :rtype: dict
        """
        return self._call('%s.info' % self._magento_model, [int(id)])


@magento
class AttributeSetDelayedBatchImport(DelayedBatchImport):
    _model_name = ['magento.attribute.set']


@magento
class AttributeSetImport(MagentoImportSynchronizer):
    _model_name = ['magento.attribute.set']


@magento
class AttributeSetImportMapper(ImportMapper):
    _model_name = 'magento.attribute.set'

    direct = [
        ('attribute_set_name', 'attribute_set_name'),
        ('attribute_set_id', 'magento_id'),
        ('sort_order', 'sort_order'), ]

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}


@magento
class AttributeSetDeleteSynchronizer(MagentoDeleteSynchronizer):
    _model_name = ['magento.attribute.set']


@magento
class AttributeSetExport(MagentoExporter):
    _model_name = ['magento.attribute.set']


@magento
class AttributeSetExportMapper(ExportMapper):
    _model_name = 'magento.attribute.set'

    direct = [
        ('attribute_set_name', 'attribute_set_name'),
        ('sort_order', 'sort_order'),
    ]

    @mapping
    def skeletonSetId(self, record):
        sess = self.session
        magento_id = sess.pool['magento.attribute.set'].get_magento_template(
            sess.cr, sess.uid, [record.id], context=sess.context)
        return {'skeletonSetId': magento_id}


# Attribute
class AttributeAttribute(orm.Model):
    _inherit = 'attribute.attribute'

    def _get_model_product(self, cr, uid, ids, idcontext=None):
        model, res_id = self.pool['ir.model.data'].get_object_reference(
            cr, uid, 'product', 'model_product_product')
        return res_id

    _columns = {
        'magento_bind_ids': fields.one2many(
            'magento.product.attribute',
            'openerp_id',
            string='Magento Bindings',),
    }

    _defaults = {
        'model_id': _get_model_product,
    }


class MagentoProductAttribute(orm.Model):
    _name = 'magento.product.attribute'
    _description = "Magento Product Attribute"
    _inherit = 'magento.binding'
    _rec_name = 'attribute_code'
    MAGENTO_HELP = "This field is a technical / configuration field for " \
                   "the attribute on Magento. \nPlease refer to the Magento " \
                   "documentation for details. "

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default['attribute_code'] = default.get('attribute_code', '') + 'Copy '
        return super(MagentoProductAttribute, self).copy(
            cr, uid, id, default, context=context)

    def _frontend_input(self, cr, uid, ids, field_names, arg, context=None):
        res={}
        for elm in self.browse(cr, uid, ids):
            field_type = elm.openerp_id.attribute_type
            map_type = {
                'char': 'text',
                'text': 'textarea',
                'float': 'price',
                'datetime': 'date',
                'binary': 'media_image',
            }
            res[elm.id] = map_type.get(field_type, field_type)
        return res

    _columns = {
        'openerp_id': fields.many2one(
            'attribute.attribute',
            string='Attribute',
            required=True,
            ondelete='cascade'),
        'attribute_code': fields.char(
            'Code',
            required=True,
            size=200,),
        'scope': fields.selection(
            [('store', 'store'), ('website', 'website'), ('global', 'global')],
            'Scope',
            required=True,
            help=MAGENTO_HELP),
        'apply_to': fields.selection([
            ('simple', 'simple'),
        ],
            'Apply to',
            required=True,
            help=MAGENTO_HELP),
        'frontend_input': fields.function(
        _frontend_input,
            method=True,
            string='Frontend input',
            type='char',
            store=False,
            help="This field depends on OpenERP attribute 'type' field "
                 "but used on Magento"),
        'frontend_label': fields.char(
            'Label', required=True, size=100, help=MAGENTO_HELP),
        'position': fields.integer('Position', help=MAGENTO_HELP),
        'group_id': fields.integer('Group', help=MAGENTO_HELP) ,
        'default_value': fields.char(
            'Default Value',
            size=10,
            help=MAGENTO_HELP),
        'note': fields.char(
            'Note', size=200, help=MAGENTO_HELP),
        'entity_type_id': fields.integer(
            'Entity Type', help=MAGENTO_HELP),
        # boolean fields
        'is_visible_in_advanced_search': fields.boolean(
            'Visible in advanced search?', help=MAGENTO_HELP),
        'is_visible': fields.boolean('Visible?', help=MAGENTO_HELP),
        'is_visible_on_front': fields.boolean(
            'Visible (front)?', help=MAGENTO_HELP),
        'is_html_allowed_on_front': fields.boolean(
            'Html (front)?', help=MAGENTO_HELP),
        'is_wysiwyg_enabled': fields.boolean(
            'Wysiwyg enabled?', help=MAGENTO_HELP),
        'is_global': fields.boolean('Global?', help=MAGENTO_HELP),
        'is_unique': fields.boolean('Unique?', help=MAGENTO_HELP),
        'is_required': fields.boolean('Required?', help=MAGENTO_HELP),
        'is_filterable': fields.boolean('Filterable?', help=MAGENTO_HELP),
        'is_comparable': fields.boolean('Comparable?', help=MAGENTO_HELP),
        'is_searchable': fields.boolean('Searchable ?', help=MAGENTO_HELP),
        'is_configurable': fields.boolean('Configurable?', help=MAGENTO_HELP),
        'is_user_defined': fields.boolean('User defined?', help=MAGENTO_HELP),
        'used_for_sort_by': fields.boolean('Use for sort?', help=MAGENTO_HELP),
        'is_used_for_price_rules': fields.boolean(
            'Used for pricing rules?', help=MAGENTO_HELP),
        'is_used_for_promo_rules': fields.boolean(
            'Use for promo?', help=MAGENTO_HELP),
        'used_in_product_listing': fields.boolean(
            'In product listing?', help=MAGENTO_HELP),
    }

    _defaults = {
        'scope': 'global',
        'apply_to': 'simple',
        'is_visible': True,
        'is_visible_on_front': True,
        'is_visible_in_advanced_search': True,
        'is_filterable': True,
        'is_searchable': True,
        'is_comparable': True,
    }

    _sql_constraints = [
        ('magento_uniq', 'unique(attribute_code)',
         "Attribute with the same code already exists : must be unique")
    ]


@magento
class ProductAttributeAdapter(GenericAdapter):
    _model_name = 'magento.product.attribute'
    _magento_model = 'product_attribute'

    def delete(self, id):
        return self._call('%s.remove'% self._magento_model,[int(id)])


@magento
class ProductAttributeDeleteSynchronizer(MagentoDeleteSynchronizer):
    _model_name = ['magento.product.attribute']


@magento
class ProductAttributeExport(MagentoExporter):
    _model_name = ['magento.product.attribute']

    def _should_import(self):
        "Attributes in magento doesn't retrieve infos on dates"
        return False


@magento
class ProductAttributeExportMapper(ExportMapper):
    _model_name = 'magento.product.attribute'

    direct = [
        ('attribute_code', 'attribute_code'), # required
        ('frontend_input', 'frontend_input'),
        ('scope', 'scope'),
        ('is_global', 'is_global'),
        ('is_filterable', 'is_filterable'),
        ('is_comparable', 'is_comparable'),
        ('is_visible', 'is_visible'),
        ('is_searchable', 'is_searchable'),
        ('is_user_defined', 'is_user_defined'),
        ('is_configurable', 'is_configurable'),
        ('is_visible_on_front', 'is_visible_on_front'),
        ('is_used_for_price_rules', 'is_used_for_price_rules'),
        ('is_unique', 'is_unique'),
        ('is_required', 'is_required'),
        ('position', 'position'),
        ('group_id', 'group_id'),
        ('default_value', 'default_value'),
        ('is_visible_in_advanced_search', 'is_visible_in_advanced_search'),
        ('note', 'note'),
        ('entity_type_id', 'entity_type_id'),
        ]

    @mapping
    def frontend_label(self, record):
        #required
        return {'frontend_label': [{
                'store_id': 0,
                'label': record.frontend_label,
            }]}


# Attribute option
class AttributeOption(orm.Model):
    _inherit = 'attribute.option'

    _columns = {
        'magento_bind_ids': fields.one2many(
            'magento.attribute.option',
            'openerp_id',
            string='Magento Bindings',),
    }


class MagentoAttributeOption(orm.Model):
    _name = 'magento.attribute.option'
    _description = ""
    _inherit = 'magento.binding'

    _columns = {
        'openerp_id': fields.many2one(
            'attribute.option',
            string='Attribute option',
            required=True,
            ondelete='cascade'),
        'name': fields.char(
            'Name',
            size=64,
            required=True),
        'is_default': fields.boolean('Is default'),
    }

    _defaults = {
        'is_default': True,
    }


@magento
class AttributeOptionAdapter(GenericAdapter):
    _model_name = 'magento.attribute.option'
    _magento_model = 'product_attribute'

    def create(self, data):
        return self._call('%s.addOption'% self._magento_model,
                          [data.pop('attribute'), data])


@magento
class AttributeOptionDeleteSynchronizer(MagentoDeleteSynchronizer):
    _model_name = ['magento.attribute.option']


@magento
class AttributeOptionExport(MagentoExporter):
    _model_name = ['magento.attribute.option']


@magento
class AttributeOptionExportMapper(ExportMapper):
    _model_name = 'magento.attribute.option'

    direct = []

    @mapping
    def label(self, record):
        return {'label': [{
                'store_id': ['0'],
                'value': record.openerp_id.name,
                }]
            }

    @mapping
    def attribute(self, record):
        #TODO [0] seems not to be valid
        magento_attribute = record.openerp_id.attribute_id.magento_bind_ids[0]
        return {'attribute': magento_attribute.magento_id}

    @mapping
    def order(self, record):
        return {'order': record.openerp_id.sequence + 1 }

    @mapping
    def is_default(self, record):
        return {'is_default': int(record.is_default)}
