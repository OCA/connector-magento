# © 2013 Guewen Baconnier,Camptocamp SA,Akretion
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


# TODO magento.delivery.carrier & move specific stuff
class DeliveryCarrier(models.Model):
    """ Adds Magento specific fields to ``delivery.carrier``

    ``magento_code``

        Code of the carrier delivery method in Magento.
        Example: ``colissimo_express``

    ``magento_tracking_title``

        Display name of the carrier for the tracking in Magento.
        Example: Colissimo Express

    ``magento_carrier_code``

        General code of the carrier, the first part of the ``magento_code``.
        Example: ``colissimo`` for the method ``colissimo_express``.

    ``magento_export_tracking``

        Defines if the tracking numbers should be exported to Magento.
    """
    _inherit = "delivery.carrier"

    magento_code = fields.Char(
        string='Magento Carrier Code',
        required=False,
    )
    magento_tracking_title = fields.Char(
        string='Magento Tracking Title',
        required=False,
    )
    # in Magento, the delivery method is something like that:
    # tntmodule2_tnt_basic
    # where the first part before the first _ is always the carrier code
    # in this example, the carrier code is tntmodule2
    magento_carrier_code = fields.Char(
        compute='_compute_carrier_code',
        string='Magento Base Carrier Code',
    )
    magento_export_tracking = fields.Boolean(string='Export tracking numbers',
                                             default=True)

    @api.depends('magento_code')
    def _compute_carrier_code(self):
        for carrier in self:
            if carrier.magento_code:
                carrier.magento_carrier_code = carrier.magento_code.split(
                    '_')[0]
