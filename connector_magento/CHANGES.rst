Changelog
---------

3.0.0 (2015-06-02)
~~~~~~~~~~~~~~~~~~

* Migrated on the new Odoo API and the new Connector API
* Extended the test coverage
* Show the failed calls in the logger with the ERROR level
* New Docker image for Magento, mentionned in the documentation
* Allow to choose a default sales team for sales orders on the storeviews
* Lot of improvements/cleaning of the code
* The binders can now return records (new ``browse`` argument)
* The Importer now pass the binding report instead of the binding_id
  internally
* Remove sale.shop

2.5.0 (2015-01-06)
~~~~~~~~~~~~~~~~~~

* The option for tax inclusion is now configurable by storeview #74
* Add a backend adapter for the product categories #58
* Add basic units to allow handling bundle products in submodules #13
* Add mechanisms for the export of records (lock of bindings, helper for dependencies export) #33
* 'New copy from quotation' rebinds the Magento order with the new copy #9
* Better memory footprint and performance on update of stock quantity #11
* Fix: Magento sometimes returns no invoice id #29
* Fix: discount_amount with a None value #70
* Fix: mapping for res.partner.title too broad (mix up "Herr and Herr Dr." #68
* Fix: error when a binding have a ID "0" which happens with Magento #61
* Fix: allow to copy a stock picking #60
* Fix: compatibility with the fiscal position rules module #42
* Fix: Prevent to create duplicate bindings on invoices #39
* Fix: Remove trailing None on calls made to the Magento's API (PHP 5.4 compatibility) #28
* Fix: avoid to send twice a tracking number #16
* Fix: when a tracking's job is executed before the export of the picking, the tracking's job export the picking #16
* Fix: replace nltk by Beautifulsoup #40
* Fix:  Add a 'to date' boundary to batch jobs #17

2.4.2 (2014-06-16)
~~~~~~~~~~~~~~~~~~

* Fix: AssertionError: Several classes found for <class 'openerp.addons.connector.unit.mapper.ImportMapper'> with session <Session db_name: pruebas, uid: 1>, model name: magento.product.product. Found: set([<class 'openerp.addons.magentoerpconnect.product.IsActiveProductImportMapper'>, <class 'openerp.addons.magentoerpconnect.product.ProductImportMapper'>])

2.4.1 (2014-06-10)
~~~~~~~~~~~~~~~~~~

* Fix: Binders should find records even if they are inactive (lp:1323719)

2.4.0 (2014-05-26)
~~~~~~~~~~~~~~~~~~

* New helper in importer to import dependencies
* allow to customize the available versions without overriding the 'version' field
* New option 'Create Invoice On' on payment methods with options 'on paid', 'on validate'
* Using Magento on PHP 5.4 without using the compatibility patch would
  break syncs'. Correct solution is to install the patch on Magento
  though! http://magento.com/blog/magento-news/magento-now-supports-php-54
* Allow to use HTTP Auth Basic to connect to the Magento API
* Retry jobs when they hit a 502, 503 or 504 error
* Added missing scheduler for import of products
* Fix: calculate correctly the discount ratio on sales order lines (lp:1201590)
* Possibility to exclude products from stock synchronizations
* Products disabled on Magento are imported disabled on OpenERP. An additional module allows more options.
* Possibility to disable import of sales orders per storeview
* Related Actions: open the form view on the record concerned by an export job, or open the Magento's admin page
  on importing jobs
* Special order lines (shipping, ...) are now the last lines of an order, not the first


2.3.1 (2014-01-23)
~~~~~~~~~~~~~~~~~~

*  Do not fail when a None value is given instead of a float when importing special lines of sales orders. (https://launchpad.net/bugs/1271537)


2.3.0 (2014-01-15 warning: API changes)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Compatibility with the Connector Framework: listeners 'on_record_create' receives
  an additional argument 'vals'; 'on_record_write's named argument 'fields' becomes 'vals'
  and receives the full dictionary of values
* Fix: wrong main image imported on products (https://launchpad.net/bugs/1258418)
* Changes calls to Mapper according to the new API of the Mappers.
  See branch: https://code.launchpad.net/~openerp-connector-core-editors/openerp-connector/7.0-connector-mapper-refactor
* Fix: mismatch between tax excluding and tax including amount, new configuration option (https://launchpad.net/bugs/1234117)
* Fix: mismatch between tax excluding and tax including amount, new configuration option (https://launchpad.net/bugs/1234117)
* Implements the new API (connector_ecommerce) for the special order lines:
  https://code.launchpad.net/~openerp-connector-core-editors/openerp-connector/7.0-e-commerce-addons-refactor-so-extra-lines/+merge/194629


2.2.1 (2013.11.22)
~~~~~~~~~~~~~~~~~~

* Fix: Error when a sales order had no shipping method
* Fix: Searching for allowed carriers incorrectly uses magento_picking_id instead of magento_order_id (https://launchpad.net/bugs/1238951)
* Fix: Import of products fails when an image is missing (404 HTTP Error)  (https://launchpad.net/bugs/1210543)
* Fix: Mapping of the states is not strict enough  (https://launchpad.net/bugs/1250136)
* Fix: get_carriers() converting Magento order ID to int, fails with edited orders (https://launchpad.net/bugs/1253743)
* Fix: Importing authorized orders ignores PayPal orders (https://launchpad.net/bugs/1252308)


2.2.0 (public release - 2013.11.06)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Option to choose if the invoices are exported to Magento on payment or validation (Thanks to Allison Miller)
* Allow to define a prefix for the name of the imported sales orders (Thanks to Augustin Cisterne-Kaas)
* Fix: 'store_id' field in the Magento API contains the id of the storeview, and was mapped with the store. In some circumstances, sales orders may fail to import. (lp:1235269)
* Support of configurable products in import of sales orders


2.1.0 (2013.08.05)
~~~~~~~~~~~~~~~~~~

* Import of partners reviewed according to https://launchpad.net/bugs/1193281
  Especially to handle the b2b use cases better.
* Fix: Magento bindings duplicated with the "copy" method (https://launchpad.net/bugs/1205239)
* Fix: 503 Service unavailable protocol error should be retried later (https://launchpad.net/bugs/1194733)
* Fix: Import of guest orders (https://bugs.launchpad.net/openerp-connector/+bug/1193239)
* 'Authorized' import rules to be able to import sales orders authorized by a payment institute but not paid yet. (Thanks to Brendan Clune)
* Define the partners relationships only on the creation of new records, allowing manual specification of company / contact relationships within OpenERP (Thanks to Brendan Clune)
* Fix: State information for partners not mapped correctly (Thanks to Brendan Clune) (https://launchpad.net/bugs/1183837)
* Many others: see the bazaar logs

2.0.0
~~~~~

* First release


..
  Model:
  2.0.1 (date of release)
  ~~~~~~~~~~~~~~~~~~~~~~~

  * change 1
  * change 2
