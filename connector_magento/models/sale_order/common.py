# © 2013 Guewen Baconnier,Camptocamp SA,Akretion
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import xmlrpc.client

import odoo.addons.decimal_precision as dp

from odoo import models, fields, api, _
from odoo.addons.connector.exception import IDMissingInBackend
from odoo.addons.queue_job.job import job
from odoo.addons.component.core import Component

from ...components.backend_adapter import MAGENTO_DATETIME_FORMAT

_logger = logging.getLogger(__name__)


class MagentoSaleOrder(models.Model):
    _name = 'magento.sale.order'
    _inherit = 'magento.binding'
    _description = 'Magento Sale Order'
    _inherits = {'sale.order': 'odoo_id'}

    odoo_id = fields.Many2one(comodel_name='sale.order',
                              string='Sale Order',
                              required=True,
                              ondelete='cascade')
    magento_order_line_ids = fields.One2many(
        comodel_name='magento.sale.order.line',
        inverse_name='magento_order_id',
        string='Magento Order Lines'
    )
    total_amount = fields.Float(
        string='Total amount',
        digits=dp.get_precision('Account')
    )
    total_amount_tax = fields.Float(
        string='Total amount w. tax',
        digits=dp.get_precision('Account')
    )
    magento_order_id = fields.Integer(string='Magento Order ID',
                                      help="'order_id' field in Magento")
    # when a sale order is modified, Magento creates a new one, cancels
    # the parent order and link the new one to the canceled parent
    magento_parent_id = fields.Many2one(comodel_name='magento.sale.order',
                                        string='Parent Magento Order')
    storeview_id = fields.Many2one(comodel_name='magento.storeview',
                                   string='Magento Storeview')
    store_id = fields.Many2one(related='storeview_id.store_id',
                               string='Storeview',
                               readonly=True)

    @job(default_channel='root.magento')
    @api.multi
    def export_state_change(self, allowed_states=None,
                            comment=None, notify=None):
        """ Change state of a sales order on Magento """
        self.ensure_one()
        with self.backend_id.work_on(self._name) as work:
            exporter = work.component(usage='sale.state.exporter')
            return exporter.run(self, allowed_states=allowed_states,
                                comment=comment, notify=notify)

    @job(default_channel='root.magento')
    @api.model
    def import_batch(self, backend, filters=None):
        """ Prepare the import of Sales Orders from Magento """
        assert 'magento_storeview_id' in filters, ('Missing information about '
                                                   'Magento Storeview')
        _super = super(MagentoSaleOrder, self)
        return _super.import_batch(backend, filters=filters)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    magento_bind_ids = fields.One2many(
        comodel_name='magento.sale.order',
        inverse_name='odoo_id',
        string="Magento Bindings",
    )

    @api.depends('magento_bind_ids', 'magento_bind_ids.magento_parent_id')
    def get_parent_id(self):
        """ Return the parent order.

        For Magento sales orders, the magento parent order is stored
        in the binding, get it from there.
        """
        super(SaleOrder, self).get_parent_id()
        for order in self:
            if not order.magento_bind_ids:
                continue
            # assume we only have 1 SO in Odoo for 1 SO in Magento
            assert len(order.magento_bind_ids) == 1
            magento_order = order.magento_bind_ids[0]
            if magento_order.magento_parent_id:
                self.parent_id = magento_order.magento_parent_id.odoo_id

    def _magento_cancel(self):
        """ Cancel sales order on Magento

        Do not export the other state changes, Magento handles them itself
        when it receives shipments and invoices.
        """
        for order in self:
            old_state = order.state
            if old_state == 'cancel':
                continue  # skip if already canceled
            for binding in order.magento_bind_ids:
                job_descr = _("Cancel sales order %s") % (binding.external_id,)
                binding.with_delay(
                    description=job_descr
                ).export_state_change(allowed_states=['cancel'])

    @api.multi
    def write(self, vals):
        if vals.get('state') == 'cancel':
            self._magento_cancel()
        return super(SaleOrder, self).write(vals)

    def _magento_link_binding_of_copy(self, new):
        # link binding of the canceled order to the new order, so the
        # operations done on the new order will be sync'ed with Magento
        if self.state != 'cancel':
            return
        binding_model = self.env['magento.sale.order']
        bindings = binding_model.search([('odoo_id', '=', self.id)])
        bindings.write({'odoo_id': new.id})

        for binding in bindings:
            # the sales' status on Magento is likely 'canceled'
            # so we will export the new status (pending, processing, ...)
            job_descr = _("Reopen sales order %s") % (binding.external_id,)
            binding.with_delay(
                description=job_descr
            ).export_state_change()

    @api.multi
    def copy(self, default=None):
        self_copy = self.with_context(__copy_from_quotation=True)
        new = super(SaleOrder, self_copy).copy(default=default)
        self_copy._magento_link_binding_of_copy(new)
        return new


class MagentoSaleOrderLine(models.Model):
    _name = 'magento.sale.order.line'
    _inherit = 'magento.binding'
    _description = 'Magento Sale Order Line'
    _inherits = {'sale.order.line': 'odoo_id'}

    magento_order_id = fields.Many2one(comodel_name='magento.sale.order',
                                       string='Magento Sale Order',
                                       required=True,
                                       ondelete='cascade',
                                       index=True)
    odoo_id = fields.Many2one(comodel_name='sale.order.line',
                              string='Sale Order Line',
                              required=True,
                              ondelete='cascade')
    backend_id = fields.Many2one(
        related='magento_order_id.backend_id',
        string='Magento Backend',
        readonly=True,
        store=True,
        # override 'magento.binding', can't be INSERTed if True:
        required=False,
    )
    tax_rate = fields.Float(string='Tax Rate',
                            digits=dp.get_precision('Account'))
    notes = fields.Char()

    @api.model
    def create(self, vals):
        magento_order_id = vals['magento_order_id']
        binding = self.env['magento.sale.order'].browse(magento_order_id)
        vals['order_id'] = binding.odoo_id.id
        binding = super(MagentoSaleOrderLine, self).create(vals)
        # FIXME triggers function field
        # The amounts (amount_total, ...) computed fields on 'sale.order' are
        # not triggered when magento.sale.order.line are created.
        # It might be a v8 regression, because they were triggered in
        # v7. Before getting a better correction, force the computation
        # by writing again on the line.
        # line = binding.odoo_id
        # line.write({'price_unit': line.price_unit})
        return binding


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    magento_bind_ids = fields.One2many(
        comodel_name='magento.sale.order.line',
        inverse_name='odoo_id',
        string="Magento Bindings",
    )

    @api.model
    def create(self, vals):
        old_line_id = None
        if self.env.context.get('__copy_from_quotation'):
            # when we are copying a sale.order from a canceled one,
            # the id of the copied line is inserted in the vals
            # in `copy_data`.
            old_line_id = vals.pop('__copy_from_line_id', None)
        new_line = super(SaleOrderLine, self).create(vals)
        if old_line_id:
            # link binding of the canceled order lines to the new order
            # lines, happens when we are using the 'New Copy of
            # Quotation' button on a canceled sales order
            binding_model = self.env['magento.sale.order.line']
            bindings = binding_model.search([('odoo_id', '=', old_line_id)])
            if bindings:
                bindings.write({'odoo_id': new_line.id})
        return new_line

    @api.multi
    def copy_data(self, default=None):
        data = super(SaleOrderLine, self).copy_data(default=default)[0]
        if self.env.context.get('__copy_from_quotation'):
            # copy_data is called by `copy` of the sale.order which
            # builds a dict for the full new sale order, so we lose the
            # association between the old and the new line.
            # Keep a trace of the old id in the vals that will be passed
            # to `create`, from there, we'll be able to update the
            # Magento bindings, modifying the relation from the old to
            # the new line.
            data['__copy_from_line_id'] = self.id
        return [data]


class SaleOrderAdapter(Component):
    _name = 'magento.sale.order.adapter'
    _inherit = 'magento.adapter'
    _apply_on = 'magento.sale.order'

    _magento_model = 'sales_order'
    _magento2_model = 'orders'
    _magento2_search = 'orders'
    _magento2_key = 'entity_id'
    _admin_path = '{model}/view/order_id/{id}'
    _admin2_path = 'sales/order/view/order_id/{id}'

    def _call(self, method, arguments, http_method=None, storeview=None):
        try:
            return super(SaleOrderAdapter, self)._call(
                method, arguments, http_method=http_method,
                storeview=storeview)
        except xmlrpc.client.Fault as err:
            # this is the error in the Magento API
            # when the sales order does not exist
            if err.faultCode == 100:
                raise IDMissingInBackend
            else:
                raise

    def search(self, filters=None, from_date=None, to_date=None,
               magento_storeview_ids=None):
        """ Search records according to some criteria
        and returns a list of ids

        :rtype: list
        """
        if filters is None:
            filters = {}
        dt_fmt = MAGENTO_DATETIME_FORMAT
        if from_date is not None:
            filters.setdefault('created_at', {})
            filters['created_at']['from'] = from_date.strftime(dt_fmt)
        if to_date is not None:
            filters.setdefault('created_at', {})
            filters['created_at']['to'] = to_date.strftime(dt_fmt)
        if magento_storeview_ids is not None:
            filters['store_id'] = {'in': magento_storeview_ids}

        if self.collection.version == '1.7':
            arguments = {
                'imported': False,
                # 'limit': 200,
                'filters': filters,
            }
        else:
            arguments = filters
        return super(SaleOrderAdapter, self).search(arguments)

    def read(self, external_id, attributes=None):
        """ Returns the information of a record

        :rtype: dict
        """
        # pylint: disable=method-required-super
        if self.collection.version == '1.7':
            return self._call('%s.info' % self._magento_model,
                              [external_id, attributes])
        return super(SaleOrderAdapter, self).read(
            external_id, attributes=attributes)

    def get_parent(self, external_id):
        if self.collection.version == '2.0':
            res = self.read(external_id)
            return res.get('relation_parent_id')
        return self._call('%s.get_parent' % self._magento_model,
                          [external_id])

    def add_comment(self, external_id, status, comment=None, notify=False):
        return self._call('%s.addComment' % self._magento_model,
                          [external_id, status, comment, notify])
