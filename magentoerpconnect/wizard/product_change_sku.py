

from osv import fields,osv
from tools.translate import _


class ProductChangeSkuWizard(osv.osv_memory):
    _name = 'product.change.sku.wizard'
    _description = 'Wizard to change SKU of a product on Magento and OpenERP'

    _columns = {
        'new_magento_sku': fields.char('New Magento SKU', size=64),
        }

    def action_change_sku(self, cr, uid, id, context=None):
        sale_shop_obj = self.pool.get('sale.shop')
        product_obj = self.pool.get('product.product')
        ext_ref_obj = self.pool.get('external.referential')

        new_magento_sku = self.read(cr, uid, id, context=context)[0]['new_magento_sku']

        product_id = context['active_ids'][0]
        # get all magento external_referentials

        for referential_id in ext_ref_obj.search(cr, uid, [('magento_referential', '=', True)]):
            conn = ext_ref_obj.external_connection(cr, uid, referential_id)
            magento_product_id = product_obj.oeid_to_extid(cr, uid, product_id, referential_id, context)
            if magento_product_id:
                conn.call('catalog_product.update',
                    [magento_product_id, {'sku': new_magento_sku}])

        # TODO: rollback on all referential if one update fail

        product_obj.write(cr, uid, product_id, {'magento_sku': new_magento_sku})

        return {'type': 'ir.actions.act_window_close'}

ProductChangeSkuWizard()
