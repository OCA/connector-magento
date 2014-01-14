from osv import osv, fields

class payment_invoice(osv.Model):
	_inherit = "payment.method"
	
	_columns = {
		'create_invoice_on': fields.selection(
            [('open', 'Validate'),
             ('paid', 'Paid')],
            'Create invoice on action',
            help="Should the invoice be created in Magento "
                 "when it is validated or when it is paid in OpenERP? If nothing is set, Create invoice on action falls back to Store Options."),
		}