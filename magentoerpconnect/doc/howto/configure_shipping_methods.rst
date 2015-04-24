.. _configure-shipping-methods:


#################################
How to configure shipping methods
#################################

Find the configuration in the menu
`Warehouse > Configuration > Delivery Methods`.

For each shipping method in Magento,
you need to create a delivery method in Odoo.

The connector creates a product `[SHIP] Shipping costs`,
you can use it for the Delivery Product.

.. note:: If you import a sale order but the shipping method does not
          exist, it will create it for you. But the configuration will
          not be correct, so you better have to create them before
          any import.

The 'Magento Carrier Code' is the code of the shipping method in Magento,
for instance: `flatrate_flatrate`.

The 'Magento Tracking Title' is the text which will be displayed on
Magento next to the tracking number.

'Export tracking numbers' defines wether the tracking numbers should be
sent to Magento.



.. warning:: If you use the `flatrate` shipping method, you need to
             deactivate the option `Export tracking numbers` because
             this shipping method does not support to send tracking
             numbers.
