.. _modify-an-order:


###################################
How to cancel / modify a sale order
###################################

****************************************
Handle a sale order cancelled on Magento
****************************************

If a sales order has already been imported in Odoo and is cancelled
in Magento, the change won't be reflected in Odoo.  If a sales order
is still waiting for a payment and is canceled, it won't be imported in
Odoo.

*******************
Modify a sale order
*******************

When you need to modify a product in a sale order,
you should not modify it in the sale order directly.
The sale order represents what the customer really ordered.

You would be able to change the product in the delivery order.
But Magento does not accept any change in the shipments,
so it won't be modified on the Magento side
(and you will have issues with partial deliveries).
The changes would not be repercuted on the invoices neither.

Instead, you can modify the sale order on the Magento backend.
When Magento modifies a sale order,
it cancels it and creates a new one.
When the new order is imported in Odoo,
it flags the old one as 'Cancelled on Backend',
then link the new order with the old one as a 'parent' order.

If it can automatically cancel the parent order,
it will do it.
Otherwise, you'll have to handle it manually.
You can search for them using the search filters.

Until the old sale order is not cancelled or done,
a rule prevents the new and the parent sales orders
to be confirmed.
