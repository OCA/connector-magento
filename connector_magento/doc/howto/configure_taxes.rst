.. _configure-taxes:


########################
How to configure taxes
########################

The connector imports products prices and sale order
line unit prices with taxes excluded by default.

If Magento is configured with prices including taxes,
you have to activate the checkbox ``Prices included tax``
in ``Connectors > Magento > Backends`` in the tab ``Advanced
Configuration``.

.. warning:: This option should respect the same
             configuration than Magento.  Pay
             attention to the taxes on the products,
             which should surely include prices when
             this option is activated.
