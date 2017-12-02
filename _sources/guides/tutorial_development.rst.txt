.. _tutorial-development:


Tutorial: development
=====================

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
:py:func:`openerp.addons.magentoerpconnect.consumer.magento_consumer` and by the event
which has to fire it::

    @on_record_write(model_names=['my.model'])
    @magento_consumer
    def my_consumer(session, model_name, record_id, vals=None):
        print 'Yeah'

.. note:: The consumers always start with the arguments ``session`` and
          ``model_name``. The next arguments vary, but they are defined
          by the :py:class:`connector.event.Event`


Find the 'connector unit' for a model
-------------------------------------

Assume that you already have a ``ConnectorEnvironment``.

.. note:: A ``ConnectorEnvironment`` is the scope where the synchronizations
          are done. It contains the browse record of the backend
          (``magento.backend``), a ``ConnectorSession`` (container for ``cr``,
          ``uid``, ``context``) and the name of the model we are working with).

You can get an instance of the ``ConnectorUnit`` to use from the
environment.  You'll need to ask a connector unit with the base class
which interests you.  Say you want a Synchronizer which import records
from Magento::

    importer = environment.get_connector_unit(MagentoImporter)

``importer`` is an instance of the importer to use for the model of the
environment.

Say you want a binder for your model::

    binder = environment.get_connector_unit(connector.Binder)

``binder`` is an instance of the binder for your model.

And so on...

.. note:: Every ``ConnectorUnit`` instance keeps the environment as
          attribute. It means that you can access to the environment
          from a synchronizer with ``self.connector_env``.

When you are already inside a ``ConnectorUnit`` though you can use the shortcuts::

    # for the current model
    importer = self.unit_for(MagentoImporter)
    # for another model
    importer = self.unit_for(MagentoImporter, model='another.model')

As the binders are the most used ``ConnectorUnit`` classes, they have a
dedicated shortcut::

    # for the current model
    binder = self.binder_for()
    # for another model
    binder = self.binder_for(model='another.model')


Create an import
----------------

You'll probably need to work with 4 connector units:

* a Synchronizer (presumably 2, we'll see why soon)
* a Mapper
* a Backend Adapter
* a Binder

You will also need to create / change the Odoo models.

.. note:: Keep in mind: try to modify at least as possible the Odoo
          models and classes.

The synchronizer will handle the flow of the synchronization. It will
get the data from Magento using the Backend Adapter, transform it using
the Mapper, and use the Binder(s) to search the relation(s) with other
imported records.

Why do we need 2 synchronizers? Because an import is generally done in 2
phases:

1. The first synchronizer searches the list of all the ids to import.
2. The second synchronizer imports all the ids atomically (in separate
   jobs).

We'll see in details a simple import: customer groups.
Customer groups are importer as categories of partners
(``res.partner.category``).

Models
''''''

First, we create the model::

    class MagentoResPartnerCategory(models.Model):
        _name = 'magento.res.partner.category'
        _inherit = 'magento.binding'
        _inherits = {'res.partner.category': 'openerp_id'}

        openerp_id = fields.Many2one(comodel_name='res.partner.category',
                                     string='Partner Category',
                                     required=True,
                                     ondelete='cascade')
        tax_class_id = fields.Integer(string='Tax Class ID')

Observations:

* We do not change ``res.partner.category`` but create a
  ``magento.res.partner.category`` model instead.
* It `_inherit` from `magento.binding`
* It contains the links to the Magento backend, the category and the
  ID on Magento (inherited from ``magento.binding``).
* This model stores the data related to one category and one Magento
  backend as well, so this data does not pollute the category and does
  not criss-cross when several backends are connected.
* It ``_inherits`` the ``res.partner.category`` so we can directly use
  this model for the imports and the exports without complications.

We need to add the field ``magento_bind_ids`` in
``res.partner.category`` to relate to the Magento Bindings::

    class ResPartnerCategory(models.Model):
        _inherit = 'res.partner.category'

        magento_bind_ids = fields.One2many(
            comodel_name='magento.res.partner.category',
            inverse_name='openerp_id',
            string='Magento Bindings',
            readonly=True,
        )


That's the only thing we need to change (besides the view) in the
Odoo's models!

.. note:: The name of the field ``magento_bind_ids`` is a convention.

Ok, we're done with the models. Now the **synchronizations**!

Batch Importer
''''''''''''''

The first Synchronizer, which get the full list of ids to import is
usually a subclass of
:py:class:`magentoerpconnect.unit.import_synchronizer.BatchImporter`.

The customer groups are simple enough to use a generic class::

    @magento
    class DelayedBatchImporter(BatchImporter):
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

* Decorated by ``@magento``: this synchronizer will be available for all
  versions of Magento. Decorated with ``@magento1700`` it would be only
  available for Magento 1.7.
* ``_model_name``: the list of models allowed to use this synchronizer
* We just override the ``_import_record`` hook, the search has already
  be done in
  :py:class:`magentoerpconnect.unit.import_synchronizer.BatchImporter`.
* ``import_record`` is a job to import a record from its ID.
* Delay the import of each record, a job will be created for each record id.
* This synchronization does not need any Binder nor Mapper, but does
  need a Backend Adapter to be able to speak with Magento.

So, let's implement the **Backend Adapter**.

Backend Adapter
'''''''''''''''

Most of the Magento objects can use the generic class
:py:class`magentoerpconnect.unit.backend_adapter.GenericAdapter`.
However, the ``search`` entry point is not implemented in the API for
customer groups.

We'll replace it using ``list`` and select only the ids::

    @magento
    class PartnerCategoryAdapter(GenericAdapter):
        _model_name = 'magento.res.partner.category'
        _magento_model = 'ol_customer_groups'

        def search(self, filters=None):
            """ Search records according to some criterias
            and returns a list of ids

            :rtype: list
            """
            return [int(row['customer_group_id']) for row
                       in self._call('%s.list' % self._magento_model,
                                     [filters] if filters else [{}])]

Observations:

* ``_model_name`` is just ``magento.res.partner.category``, this adapter
  is available only for this model.
* ``_magento_model`` is the first part of the entry points in the API
  (ie. ``ol_customer_groups.list``)
* Only the ``search`` method is overriden.

We have all the pieces for the first part of the synchronization, just
need to...

Delay execution of our Batch Import
'''''''''''''''''''''''''''''''''''

This import will be called from the **Magento Backend**, we inherit ``magento.backend``
and add a method (and add in the view as well, I won't write the view's xml here)::

    class MagentoBackend(models.Model):
        _inherit = 'magento.backend'

        @api.multi
        def import_customer_groups(self):
            session = ConnectorSession.from_env(self.env)
            for backend_id in self.ids:
                job.import_batch.delay(session, 'magento.res.partner.category',
                                       backend_id)

            return True

Observations:

* Encapsulate Odoo environment in a :py:class:`openerp.addons.connector.session.ConnectorSession`.
* Delay the job ``import_batch`` when we click on the button.
* if the arguments were given to ``import_batch`` directly (without the
  ``.delay()``, the import would be done synchronously.

Overview on the jobs
''''''''''''''''''''

We use 2 jobs: ``import_record`` and ``import_batch``. These jobs are
already there so you don't need to write them, but we can have a look
on them to understand what they do::

    def _get_environment(session, model_name, backend_id):
        model = session.env['magento.backend']
        backend_record = model.browse(backend_id)
        return connector.Environment(backend_record, session, model_name)


    @connector.job
    def import_batch(session, model_name, backend_id, filters=None):
        """ Prepare a batch import of records from Magento """
        env = _get_environment(session, model_name, backend_id)
        importer = env.get_connector_unit(BatchImporter)
        importer.run(filters)


    @connector.job
    def import_record(session, model_name, backend_id, magento_id):
        """ Import a record from Magento """
        env = _get_environment(session, model_name, backend_id)
        importer = env.get_connector_unit(MagentoImporter)
        importer.run(magento_id)

Observations:

* Decorated by :py:class:`connector.queue.job.job`, allow to
  ``delay`` the function.
* We create a new environment and ask for the good importer, respectively
  for batch imports and record imports. The environment returns an
  instance of the importer to use.
* The docstring of the job is its description for the user.

At this point, if one click on the button to import the categories, the
batch import would run, generate one job for each category to import,
and then all these jobs would fail. We need to create the second
synchronizer, the mapper and the binder.

Record Importer
'''''''''''''''

The import of customer groups is so simple that it can use a generic
class
:py:class:`openerp.addons.magentoerpconnect.unit.import_synchronizer.SimpleRecordImporter`.
We just need to add the model in the ``_model_name`` attribute::

    @magento
    class SimpleRecordImporter(MagentoImporter):
        """ Import one Magento Website """
        _model_name = [
                'magento.website',
                'magento.store',
                'magento.storeview',
                'magento.res.partner.category',
            ]

However, most of the imports will be more complicated than that. You
will often need to create a new class for a model, where you will need
to use some of the hooks to change the behavior
(``_import_dependencies``, ``_after_import`` for example).
Refers to the importers already created in the module and to the base
class
:py:class:`openerp.addons.magentoerpconnect.unit.import_synchronizer.MagentoImporter`.

The synchronizer asks to the appropriate :py:class:`~connector.unit.mapper.Mapper`  to transform the data
(in ``_map_data``). Here is how we'll create the :py:class:`~connector.unit.mapper.Mapper`.

Mapper
''''''

The :py:class:`connector.unit.mapper.Mapper` takes the record from Magento, and generates the Odoo
record. (or the reverse for the export Mappers)

The mapper for the customer groups is as follows::

    @magento
    class PartnerCategoryImportMapper(connector.ImportMapper):
        _model_name = 'magento.res.partner.category'

        direct = [('customer_group_code', 'name'),
                  ('tax_class_id', 'tax_class_id'),
                  ]

        @mapping
        def magento_id(self, record):
            return {'magento_id': record['customer_group_id']}

        @mapping
        def backend_id(self, record):
            return {'backend_id': self.backend_record.id}


Observations:

* Some mappings are in ``direct`` and some use a method with a
  ``@mapping`` decorator.
* Methods allow to have more complex mappings. (see documentation on
  :py:class:`~connector.unit.mapper.Mapper`)


Binder
''''''

For the last piece of the construct, it will be an easy one, because
normally all the Magento Models will use the same Binder, the so called
:py:class:`~openerp.addons.magentoerpconnect.unit.binder.MagentoModelBinder`.

We just need to add our model in the ``_model_name`` attribute::

    @magento
    class MagentoModelBinder(MagentoBinder):
        """
        Bindings are done directly on the model
        """
        _model_name = [
                'magento.website',
                'magento.store',
                'magento.storeview',
                'magento.res.partner.category',
            ]

    [...]

