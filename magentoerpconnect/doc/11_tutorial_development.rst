.. _tutorial-development:


Tutorial: development
=====================

This tutorial demonstrates some features of ERPpeek in the interactive
shell.

This tutorial explains how to take part in the development of
Magentoerpconnect. It will explain how to use the different pieces of
the ``Connector`` addon to synchronize records with Magento.

.. contents:: Sections:
   :local:
   :backlinks: top


Run a function on an Event
--------------------------

3 events are registered in the ``Connector`` addon:

* ``on_record_create``
* ``on_record_write``
* ``on_record_unlink``

If you need to create a new :py:class:`connector.event.Event`, please
refer to the ``Connector`` documentation.

When a function has to be run when an event is fired, it must be
registered on this event. Those functions are called ``Consumers``.

In ``magentoerpconnect/consumer.py``, some consumers are already
defined. You can add your one, it should be decorated by
:py:func:`magentoerpconnect.consumer.magento_consumer` and by the event
which has to fire it::

    @on_record_write(model_names=['my.model'])
    @magento_consumer
    def my_consumer(session, model_name, record_id, fields=None):
        print 'Yeah'

.. note:: The consumers always start with the arguments ``session`` and
          ``model_name``. The next arguments vary, but they are defined
          by the :py:class:`connector.event.Event`


Create an import
----------------

You'll need to work on at least 4 pieces of the connector:

* a Synchronizer (presumably 2, we'll why)
* a Mapper
* a Backend Adapter
* a Binder

You will also need to create / change the OpenERP models.

.. note:: Keep that in mind: try to modify at least as possible the
          OpenERP models and classes.

The synchronizer will handle the flow of the synchronization. It will
get the data from Magento using the Backend Adapter, transform it using
the Mapper, and use the Binder(s) to search the relation(s) with other
imported records.

Why do we need 2 synchronizers? Because an import is generally done in 2
phases:

1. The first synchronizer searches the list of all the ids to import.
2. The second synchronizer imports all the ids atomically.

We'll see in details a simple import: customer groups.

First, we'll create the model::

    class magento_res_partner_category(orm.Model):
        _name = 'magento.res.partner.category'
        _inherit = 'magento.binding'
        _inherits = {'res.partner.category': 'openerp_id'}

        _columns = {
            'openerp_id': fields.many2one('res.partner.category',
                                           string='Partner Category',
                                           required=True,
                                           ondelete='cascade'),
            'tax_class_id': fields.integer('Tax Class ID'),
        }

        _sql_constraints = [
            ('magento_uniq', 'unique(backend_id, magento_id)',
             'A partner tag with same ID on Magento already exists.'),
        ]

Observations:

* We do not change ``res.partner.category`` but create a
  ``magento.res.partner.category`` model instead.
* It `_inherit` from `magento.binding`
* It contains the links to the Magento backend, the category and the
  ID on Magento.
* This model stores the data related to one category and one Magento
  backend as well, so this data does not pollute the category and does
  not criss-cross when several backends are connected.
* It ``_inherits`` the ``res.partner.category`` so we can directly use
  this model for the imports and the exports without complications.

We need to add the field ``magento_bind_ids`` in
``res.partner.category`` to relate to the Magento Bindings::

    class res_partner_category(orm.Model):
        _inherit = 'res.partner.category'

        _columns = {
            'magento_bind_ids': fields.one2many(
                'magento.res.partner.category',
                'openerp_id',
                string='Magento Bindings',
                readonly=True),
        }

That's the only thing we need to change (besides the view) on the
OpenERP category!

.. note:: The name of the field ``magento_bind_ids`` is a convention.

Ok, we're done with the models. Now the synchronizations!

The first Synchronizer, which get the full list of ids to import is
usually a subclass of
:py:class:`magentoerpconnect.unit.import_synchronizer.BatchImportSynchronizer`.

The customer groups are simple enough to use a generic class::

    @magento
    class DelayedBatchImport(BatchImportSynchronizer):
        """ Delay import of the records """
        _model_name = [
                'magento.res.partner.category',
                ]

        def _import_record(self, record):
            """ Delay the import of the records"""
            job.import_record.delay(self.session,
                                    self.model._name,
                                    self.backend_record.id,
                                    record)

Observations:

* Decorated by ``@magento``: it means that this synchronizer will be
  available for all versions of Magento. If it was available only for
  Magento 1.7, I would have decorated it with ``@magento1700``.
* ``_model_name``: the list of models synchronized, we'll be able to
  just drop new model names here later.
* We just override the ``_import_record`` hook, the search has already
  be done in
  :py:class:`magentoerpconnect.unit.import_synchronizer.BatchImportSynchronizer`.
* Here, we delay the import of each record, that means a job will be
  created for each record id.
* This synchronization does not need any Binder nor Mapper, but does
  need a Backend Adapter to be able to speak with Magento!

So, let's implement the **Backend Adapter**::
