.. _tutorial-customize:


#################################
Tutorial: customize the connector
#################################

This tutorial will explain how you can customize several parts of the
connector in your own Odoo module. It assumes that you already have
some knowledge in the Odoo development. You can still refer to the
`official Odoo documentation`_.

Reading the `Connector Framework`_ documentation is also a good idea.


.. contents:: Sections:
   :local:
   :backlinks: top


.. _official Odoo documentation: https://www.odoo.com/documentation/10.0/
.. _Connector Framework: http://www.odoo-connector.com

***************************************
Bootstrap your own customization module
***************************************

You should never make changes in the official modules, instead, you need
to create your own module and apply your personalizations from there.

As an example, throughout this tutorial, we'll create our own customization
module, we'll name it, in a very original manner,
``connector_magento_customize_example``. The final example module can be found
in the root of the ``connector-magento`` repository.

Common Odoo files
=================

A ``connector_magento`` customization module is like any Odoo module,
so you will first need to create the **manifest**
``connector_magento_customize_example/__manifest__.py``:

.. literalinclude:: ../../../connector_magento_customize_example/__manifest__.py
   :language: python
   :lines: 5-15
   :emphasize-lines: 3-4

Nothing special but 2 things to note:

* It depends from ``connector_magento``.
* The module category should preferably be ``Connector``.

Of course, you also need to create the ``__init__.py`` file where you will
put the imports of your python modules.


Use it in Odoo
==============

In the next chapter, we'll cover the most common personalization:
`Add mappings of fields`_.


.. _add-custom-mappings:

**********************
Add mappings of fields
**********************

The mappings of the fields define how the fields are related between Odoo and Magento.

They defines whether field `A` should be written in field `B`, whether
it should be converted then written to `C` and `D`, etc.

To be able to customize the mappings, you need to already have a
customization module. If that's not already done, you can go through the
previous chapter: `Bootstrap your own customization module`_.

We'll see how to map new fields on the imports.

A bit of theory
===============

The mappings of the fields are defined in "Mappers" components whcih class is
:py:class:`~connector.unit.mapper.Mapper`.

.. note:: The connector almost never works with the Odoo Models
          directly. Instead, it works with its own models, which
          ``_inherits`` (note the final ``s``) the base models. For
          instance, the Magento model for ``res.partner`` is
          ``magento.res.partner``. That's why you'll see
          ``magento.res.partner`` below.

          More details in `Magento Models`_.

When you need to change the mappings, you'll need to dive in the
``connector_magento``'s code and locate the component which does this job for
your model. You won't change anything in this class, but you'll extend
it so you need to have a look on it.  For example, the mapping for
``magento.res.partner`` in ``connector_magento`` is the following
(excerpt):

.. code-block:: python

  class PartnerImportMapper(Component):
      _name = 'magento.partner.import.mapper'
      _inherit = 'magento.import.mapper'
      _apply_on = 'magento.res.partner'

      direct = [
          ('email', 'email'),
          ('dob', 'birthday'),
          (normalize_datetime('created_at'), 'created_at'),
          (normalize_datetime('updated_at'), 'updated_at'),
          ('email', 'emailid'),
          ('taxvat', 'taxvat'),
          ('group_id', 'group_id'),
      ]

      @only_create
      @mapping
      def is_company(self, record):
          # partners are companies so we can bind
          # addresses on them
          return {'is_company': True}

      @mapping
      def names(self, record):
          parts = [part for part in (record['firstname'],
                                     record['middlename'],
                                     record['lastname']) if part]
          return {'name': ' '.join(parts)}

Here we can see 2 types of mappings:

* ``direct`` mappings, a field in Magento is directly written in the
  Odoo field. The Magento field is on the left, the Odoo one is on
  the right.
* methods decorated with ``@mapping``, when the mapping is more complex
  and need to apply some logic. The name of the methods is meaningless.
  They should return a ``dict`` with the field(s) to update and their
  values. A ``None`` return value will be ignored.
* the ``record`` argument receives the Magento record.

.. note:: This is not covered here, but for the export mapppers, an
          additional decorator ``@changed_by()`` is used to filter the
          mappings to apply according to the fields modified in Odoo.


Magento Models
==============

As said in the previous section, the connector uses its own models
on top of the base ones. The connector's models are usually in the form
``magento.{model_name}``.

Basically, a Magento Model is an ``_inherits`` from the base model, so
it knows all the original fields along with its own. Its own fields are
the ID of the record on Magento, the ``many2one`` relations to the
``magento.backend`` or to the ``magento.website`` and the attributes
which are peculiar to Magento.

Example with an excerpt of the fields for ``magento.res.partner``:

* ``odoo_id``: ``Many2one`` to the ``res.partner`` (``_inherits``)
* ``backend_id``: ``Many2one`` to the ``magento.backend`` model (Magento
  Instance), for the partner this is a ``related`` because we already
  have a link to the website, itself associated to a ``magento.backend``.
* ``website_id``: ``Many2one`` to the ``magento.website`` model
* ``external_id``: the ID of the customer on Magento
* ``group_id``: ``Many2one`` to the ``magento.res.partner.category``,
  itself a Magento model for ``res.partner.category`` (Customer Groups)
* ``created_at``: created_at field from Magento
* ``taxvat``: taxvat field from Magento
* and all the fields from ``res.partner``

This datamodel allows to:

* Share the same ``res.partner`` with several ``magento.website``  (or
  even several ``magento.backend``) as we can have as many
  ``magento.res.partner`` as we want on top of a ``res.partner``.
* The values can be different for each website or backend


.. note:: In the mappings, we'll write some fields on ``res.partner``
          (via ``_inherits``) and some on ``magento.res.partner``. When
          we want to add a new field, we have to decide where to add it.
          That's a matter of: does it make more sense do have this data
          on the base model rather than on the Magento's one and should
          this data be shared between all websites / backends?

Examples
========

Example 1.
----------

I want to import the field ``created_in`` from customers.

I add it on ``magento.res.partner`` because it doesn't make sense on
``res.partner``.

For this field, the Magento API returns a string. I add it in
``connector_magento_customize_example/models/partner.py`` (I willingly skip the
part 'add them in the views'):


.. literalinclude:: ../../../connector_magento_customize_example/models/partner.py
   :language: python
   :lines: 7,14-18


And I extend the partner's mapper:

.. literalinclude:: ../../../connector_magento_customize_example/models/partner.py
   :language: python
   :lines: 8,34-41


And that's it! The field will be imported along with the other fields.


Example 2.
----------

I want to import the ``gender`` field. This one is a bit special because
Magento maps 'Male' to ``123`` and 'Female' to ``124``. They are surely
the identifiers of the attributes in Magento, and there's maybe an entry
point in the API to get the proper values, but for the sake of the
example, we'll assume we can hard-code theses values in the mappings.

This time, I will create the field in ``res.partner``, because the value
will likely be the same even if we have many ``magento.res.partner`` and
this information can be useful at this level.

.. literalinclude:: ../../../connector_magento_customize_example/models/partner.py
   :language: python
   :lines: 7,20-29


This is not a `direct` mapping, I will use a method to define the
``gender`` value:

.. literalinclude:: ../../../connector_magento_customize_example/models/partner.py
   :language: python
   :lines: 8,9,34-36,42-46

The ``gender`` field will now be imported.

********************
Customizing importer
********************

Let's say we want to plug something at the end of the partner importer.

We can do that with an inherit:

.. literalinclude:: ../../../connector_magento_customize_example/models/partner.py
   :language: python
   :lines: 8,48-54


********
And now?
********

With theses principles, you should now be able to extend the original
mappings and add your own ones. This is applicable for the customers but
for any other model actually imported as well.
