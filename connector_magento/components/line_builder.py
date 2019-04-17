# © 2017 Hibou Corp.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

"""

Line Builders for Magento psudo-payment methods (Store Credit, Rewards...).

"""

from odoo.addons.component.core import Component


class StoreCreditLineBuilder(Component):
    """ Return values for a Store Credit line """

    _name = 'magento.order.line.builder.store_credit'
    _inherit = 'ecommerce.order.line.builder'
    _usage = 'order.line.builder.magento.store_credit'

    def __init__(self, work_context):
        super(StoreCreditLineBuilder, self).__init__(work_context)
        self.product_ref = ('connector_magento',
                            'product_product_store_credit')
        self.sign = -1
        self.sequence = 991


class RewardsLineBuilder(Component):
    """ Return values for a Rewards line """

    _name = 'magento.order.line.builder.rewards'
    _inherit = 'ecommerce.order.line.builder'
    _usage = 'order.line.builder.magento.rewards'

    def __init__(self, work_context):
        super(RewardsLineBuilder, self).__init__(work_context)
        self.product_ref = ('connector_magento',
                            'product_product_rewards')
        self.sign = -1
        self.sequence = 992
