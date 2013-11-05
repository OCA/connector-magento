.. _configure-taxes:


########################
How to configure taxes
########################

The connector imports products prices and sale order
line unit prices with taxes excluded by default.

**********************************
`Prices include tax` mode
**********************************

Prices can include taxes.
Find the configuration in the menu 
`Connectors > Magento > Backends` in `Advanced 
Configuration` tab & check `Prices included tax`.

.. warning:: If you active this setting, you need to check
             `Tax Included in Price` on each taxes used by
             your Magento OpenERP flow.
             (`Accounting > Configuration > Taxes > Taxes`)

