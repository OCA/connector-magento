.. _configure-schedulers:

###########################
How to configure schedulers
###########################

Once your configuration has been set,
you will want to automate the import
of the products, sales orders, stock quantities and so on.

Go to `Settings > Technical > Automation > Scheduled Actions`.

Activate the wanted schedulers:

* Magento - Import Customer Groups

* Magento - Import Partners

* Magento - Import Product Categories

* Magento - Import Products

* Magento - Import Sales Orders

* Magento - Update Stock Quantities

You can change the `Interval Number` and `Interval Unit` as well.

------------------
Order import delay
------------------

On the Magento backend itself you can configure an import delay. This delay is
applied when fetching orders. Orders are fetched per timeframe, from the last
import date up to the current timeframe, minus the delay (in minutes).

The use case for this delay is the following combination of factors:

* New orders are fetched frequently (every x minutes)
* Orders are only imported when they are paid
* Payment is processed externally and asynchronously so that orders are
  confirmed in Magento sometime before they are marked as paid

Depending on the delay at the payment provider, configuring a delay of one or
two minutes might be enough to prevent the Magento connector from importing
many orders twice (once unpaid and only then, paid).
