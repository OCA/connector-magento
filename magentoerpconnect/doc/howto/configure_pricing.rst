.. _configure-pricing:


########################
How to configure pricing
########################

**********************************
Prices are shared accross websites
**********************************

The pricelist used for the prices sent to Magento is configured on the
Magento Backend (`Connectors > Magento > Backends`).

*************************************
Prices are different accross websites
*************************************

.. note:: Verify that the option `Use pricelists to adapt your price per
          customers` is active in the OpenERP `Settings > Configuration
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
