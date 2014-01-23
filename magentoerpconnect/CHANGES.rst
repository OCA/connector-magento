Changelog
---------


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
