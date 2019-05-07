# -*- coding: utf-8 -*-
import logging

from contextlib import contextmanager

from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class MagentoBackend(models.Model):
    _inherit = 'magento.backend'

    @api.model
    def retrieve_dashboard(self):
        values = {}
        date_midnight = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        # job data
        failed_jobs = self.env['queue.job'].search([('state', '=', 'failed')])
        running_jobs = self.env['queue.job'].search([('state', '=', 'started')])
        pending_jobs = self.env['queue.job'].search([('state', '=', 'pending')])
        values.update({
            'nr_failed_jobs': len(failed_jobs),
            'nr_running_jobs': len(running_jobs),
            'nr_pending_jobs': len(pending_jobs),
        })
        # product data
        products_simple = self.env['magento.product.product'].search_count([('product_type', '=', 'simple')])
        products_configurable = self.env['magento.product.template'].search_count([('product_type', '=', 'configurable')])
        products_sets = self.env['magento.product.bundle'].search_count([])
        values.update({
            'nr_simple_products': int(products_simple),
            'nr_configurable_products': int(products_configurable),
            'nr_set_products': int(products_sets),
        })
        # category_data
        # TODO
        # sale data
        orders = self.env['magento.sale.order'].search([('state', 'not in', ('draft', 'canceled'))])
        order_amount = sum(orders.mapped('amount_total'))
        orders_today = orders.filtered(lambda f: f.date_order > date_midnight)
        order_amount_today = sum(orders_today.mapped('amount_total'))
        values.update({
            'nr_orders_today': len(orders_today),
            'amount_orders_today': order_amount_today,
            'nr_orders_total': len(orders),
            'amount_orders_total': order_amount,
        })
        # invoice data
        invoices = self.env['magento.account.invoice'].search([('type', '=', 'out_invoice'), ('state', 'in', ('open', 'paid'))])
        invoice_amount = sum(invoices.mapped('amount_total'))
        invoices_today = invoices.filtered(lambda f: f.date_invoice > date_midnight)
        invoice_amount_today = sum(invoices_today.mapped('amount_total'))
        values.update({
            'nr_invoices_today': len(invoices_today),
            'amount_invoices_today': invoice_amount_today,
            'nr_invoices_total': len(invoices),
            'amount_invoices_total': invoice_amount,
        })
        # partner data
        partners = self.env['magento.res.partner'].search([('customer', '=', True)])
        partners_today = invoices.filtered(lambda f: f.date_created > date_midnight)
        values.update({
            'nr_partner_today': len(partners_today),
            'nr_partner_total': len(partners),
        })
        # dates
        # values.update({
        #     'import_products_from_date':
        #     'import_product_templates_from_date':
        #     'import_product_bundles_from_date':
        #     'import_categories_from_date'
        # })
        return values
