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


.. todo:: Technical note for the implementation:
          When an order is cancelled on Magento:

            1. flag SO.cancelled_on_backend
            #. try to cancel the SO (beware of picking, invoice, payments)
               2a. if successed, flag SO.cancellation_resolved
            #. the picking and invoice of the SO blocks confirmation when
               cancelled_on_backend is True and
               cancellation_resolved is False

          When an order has a 'parent_id' (modification of order)

            1. get the list of all the parent SO
            #. add a link to the parent SO
            #. sale_exception blocks when a parent SO is
               cancelled_on_backend but not cancellation_resolved

          Add search filters for cancelled_on_backend is True and
          cancellation_resolved is False

          Beware! The new order can be linked to many parent orders
          and some of them maybe do not exist in OpenERP because they
          have been cancelled before their importation.
