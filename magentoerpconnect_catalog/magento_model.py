from openerp.osv import fields, orm

class magento_backend(orm.Model):
    _inherit = 'magento.backend'
    _columns = {
    	'push_on_save': fields.boolean('Export record on save')
    }