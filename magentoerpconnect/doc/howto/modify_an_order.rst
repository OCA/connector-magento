.. _modify-an-order:


###################################
How to cancel / modify a sale order
###################################

.. warning:: This has not been implemented yet but serves
             as specifications for the ongoing implementation.


****************************************
Handle a sale order cancelled on Magento
****************************************

When a sale order is cancelled from Magento,
a flag 'Cancelled on Backend' will be activated.

You can search for them using the search filters.


*******************
Modify a sale order
*******************

When you need to modify a product in a sale order,
you should not modify it in the sale order directly.
The sale order represents what the customer really ordered.

You could change the product in the delivery order.
But Magento does not accept any change in the shipments,
so it won't be modified on the Magento side
(and you will have issues with partial deliveries).
The changes would not be repercuted on the invoices neither.

Instead, you can modify the sale order on the Magento backend.
When Magento modifies a sale order,
it cancels it and creates a new one.
When the new order is imported in OpenERP,
it flags the old one as 'Cancelled on Backend',
then link the new order with the old one.

Until the old sale order is not cancelled or done,
a rule prevents the new sale order to be confirmed.
