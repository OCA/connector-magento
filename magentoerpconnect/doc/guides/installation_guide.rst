.. _installation-guide:


##################
Installation Guide
##################


************
Installation
************

OpenERP
=======

Download the branches where you installed OpenERP::

    $ bzr branch lp:openerp-connector/7.0 connector
    $ bzr branch lp:openerp-connector/7.0-e-commerce-addons e-commerce-addons
    $ bzr branch lp:openerp-connector/7.0-magentoerpconnect magentoerpconnect
    $ bzr branch lp:openerp-product-attributes/7.0 openerp-product-attributes

Add the branches in the addons path, either using the server command
line or adding them in the OpenERP server configuration file.

In OpenERP, update the modules list using `Settings > Modules > Update
Modules List`.

Go to the menu `Settings > Modules > Installed Modules`, remove the
`Installed` filter and search for `Magento Connector`, then click on
`Install`.

Magento
=======

For the time being, the Magento extension originally built by OpenLabs
is still used  by the connector. But the version published on `Magento
Connect` is outdated.

Download the following branch and install it in Magento::

    $ bzr branch lp:magentoerpconnect/magento-module-oerp6.x-stable magento-module

In order to install it:

1. Move the `Openlabs` folder in the
   `magento_root/app/code/community`.
#. Move the file `app/etc/modules/Openlabs_OpenERPConnector.xml` in
   `magento_root/app/etc/modules`.
#. Flush the Magento cache from the admin panel or by removing everything in
   `magento_root/var/cache`

Configuring the Magento web-services
====================================

1. In the Magento admin panel, go to `System > Web-Services >
   SOAP/XML-RPC - Roles`.
#. Create a new role named `openerp` with access to `All` resources.
#. In `System > Web-Services > SOAP/XML-RPC - Users`, create a new user
   named as you want, for instance `openerp_connect`, and an API key.
   In `User Role`, choose the `openerp` role.


**********************
After the installation
**********************

Once the addon is installed, you may want to:

1. Read or read again :ref:`key-questions`

#. Assign the `Connector Manager` group on your user.

#. Create the Backend in `Connectors > Magento > Backend`,
   use the role created in `Configuring the Magento web-services`_.

#. Synchronize the initial metadata using the button `Synchronize Metadata` on the backend.

#. Configure the translations if you use them: :ref:`configure-translations`

#. Configure: :ref:`configure-emails`

#. Configure: :ref:`configure-payment-methods`

#. Configure: :ref:`configure-automatic-workflows`

#. Configure: :ref:`configure-shipping-methods`

#. Configure: :ref:`configure-warehouses`

#. Configure: :ref:`configure-pricing`

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
