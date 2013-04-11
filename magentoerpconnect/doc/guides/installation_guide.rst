.. _installation-guide:


##################
Installation Guide
##################


************
Installation
************

TODO: step-by-step installation guide from branches

**********************
After the installation
**********************

Once the addon is installed, you may want to:

1. Read or read again :ref:`key-questions`

#. Assign the `Connector Manager` group on your user.

#. Create the Backend in `Connectors > Magento > Backend`

#. Synchronize the initial metadata using the button `Synchronize Metadata` on the backend.

#. Configure the translations if you use them: :ref:`configure-translations`

#. Configure: :ref:`configure-emails`

#. Configure: :ref:`configure-payment-methods`

#. Configure: :ref:`configure-automatic-workflows`

#. Configure: :ref:`configure-shipping-methods`

#. Configure: :ref:`configure-warehouses`

On the backend,

#. Import the customer groups

#. Optionally, import the partners, otherwise they
   will be imported on the fly with the sales orders

#. Import the product categories

#. Configure the default values (accounting, ...)
   of the new categories, using the :ref:`connector-checkpoint`

#. Import the products

#. Configure the new products (accounting, suppliers, stock rules, ...)
   of the new products, using the :ref:`connector-checkpoint`

#. Create an inventory for your products

#. Update the stock quantities on Magento

#. Import the sales orders

#. Once you are all done and happy, configure the schedulers: :ref:`configure-schedulers`


****************
On a daily basis
****************

* :ref:`connector-checkpoint`
* :ref:`monitor-resolve-jobs`
