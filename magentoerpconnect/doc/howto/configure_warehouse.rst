.. _configure-warehouses:

###########################
How to configure warehouses
###########################

The warehouse defined on the Magento Backend
(`Connectors > Magento > Backend`) is the
warehouse used to update the stock quantities on Magento.

On the backend, you can also change the field from which the
stock quantity is read in the product.
By default, the quantity send to Magento is the forecasted quantity,
but you can use another standard or custom field by changing the field
`Stock Field`.

For each Magento Store, the connector has created an Odoo Sale Shop.
So you may want to check the Sales Shops to ensure they have the correct
warehouses.
