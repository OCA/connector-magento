.. _configure-pricing:


########################
How to configure pricing
########################

Install the pricing extensions by going in: `Settings > Configuration >
Connector` and by checking the `Price are managed in Odoo with
pricelists` option.

**********************************
Prices are shared accross websites
**********************************

The pricelist used for the prices sent to Magento is configured on the
Magento Backend (`Connectors > Magento > Backends`).

*************************************
Prices are different accross websites
*************************************

.. note:: Verify that the option `Use pricelists to adapt your price per
          customers` is active in the Odoo `Settings > Configuration
          > Sales`.

The pricelist used for the prices sent to Magento is configured on the
Magento Backend (`Connectors > Magento > Backends`). Magento will use
theses prices as default prices.

.. note:: In Magento, the default is to share the prices between websites.
          If you want to have different prices per websites, go to
          `System > Catalog > Catalog > Price` and set the `Catalog
          Price Scope` to `Website` instead of `Global`.

When you need different prices for a website, set the pricelist for this
website in `Connectors > Magento > Websites`.

.. warning:: The prices are actually updated on Magento when the price
             is changed on the products, not when a pricelist is
             modified.
