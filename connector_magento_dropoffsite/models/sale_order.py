# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping


class SaleOrderImportMapper(Component):

    _inherit = 'magento.sale.order.mapper'
    
    def get_site_info(self, order_id, values):
        adapter = self.component(usage='backend.adapter',
                                    model_name='magento.sale.order')
        
        res = eval(adapter._call('relaiscolis/getRelaisInfo/%s' % str(order_id), None))
        if res:
            res = res[0]
            code = res['rel']
            site = self.env['dropoff.site'].search([('carrier_id', '=', values['carrier_id']),
                                                    ('code', '=', code)])
            country = self.env['res.country'].search([('code', '=', 'FR'),])
            if site:
                site.write({'name': res['nom'],
                            'street': res['reladr'],
                            'zip': res['relcp'],
                            'city': res['relvil'],
                            'country': country[0].id})
            else:               
                site = self.env['dropoff.site'].create({'code': code,
                                                        'carrier_id': values['carrier_id'],
                                                        'name': res['nom'],
                                                        'street': res['reladr'],
                                                        'zip': res['relcp'],
                                                        'city': res['relvil'],
                                                        'country': country[0].id})
            values.update({
                'partner_id': self.options.partner_id,
                'partner_invoice_id': self.options.partner_invoice_id,
                'partner_shipping_id': site.partner_id.id,
                'final_shipping_partner_id': self.options.partner_shipping_id,
            })
        return values
            
    
    def _add_dropoff_site(self, map_record, values):
        magento_order_id = map_record.source.get('entity_id')
        values = self.get_site_info(magento_order_id, values)
        return values
    
    def finalize(self, map_record, values):
        values.setdefault('order_line', [])
        values = self._add_shipping_line(map_record, values)
        values = self._add_cash_on_delivery_line(map_record, values)
        values = self._add_gift_certificate_line(map_record, values)
        if 'carrier_id' in values and \
            self.env['delivery.carrier'].browse(values['carrier_id']).with_dropoff_site:
            values = self._add_dropoff_site(map_record, values)
        else:    
            values.update({
                'partner_id': self.options.partner_id,
                'partner_invoice_id': self.options.partner_invoice_id,
                'partner_shipping_id': self.options.partner_shipping_id,
            })
        onchange = self.component(
            usage='ecommerce.onchange.manager.sale.order'
        )
        return onchange.play(values, values['magento_order_line_ids'])
    