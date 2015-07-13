.. _tutorial-customize:


#################################
Tutorial: customize the connector
#################################

This tutorial will explain how you can customize several parts of the
connector in your own Odoo module. It assumes that you already have
some knowledge in the Odoo development. You can still refer to the
`official Odoo documentation`_.


.. contents:: Sections:
   :local:
   :backlinks: top


.. _official Odoo documentation: https://www.odoo.com/documentation/8.0/

***************************************
Bootstrap your own customization module
***************************************

You should never make changes in the official modules, instead, you need
to create your own module and apply your personalizations from there.

As an example, throughout this tutorial, we'll create our own
customization module, we'll name it, in a very original manner,
``customize_example``. The final example module can be found in the root
of the ``connector-magento`` repository.

Common Odoo files
=================

A ``magentoerpconnect`` customization module is like any Odoo module,
so you will first need to create the **manifest**
``customize_example/__openerp__.py``:

.. code-block:: python
   :emphasize-lines: 4,5

    # -*- coding: utf-8 -*-
    {'name': 'Magento Connector Customization',
     'version': '1.0.0',
     'category': 'Connector',
     'depends': ['magentoerpconnect',
                 ],
     'author': 'Myself',
     'license': 'AGPL-3',
     'description': """
    Magento Connector Customization
    ===============================

    Explain what this module changes.
    """,
     'data': [],
     'installable': True,
     'application': False,
    }

Nothing special but 2 things to note:

* It depends from ``magentoerpconnect``.
* The module category should preferably be ``Connector``.

Of course, you also need to create the ``__init__.py`` file where you will
put the imports of your python modules.

Install the module in the connector
===================================

Each new module needs to be plugged in the connector's framework.
That's just a matter of following a convention and creating
``connector.py`` in which you will call the
``install_in_connector`` function::

    from openerp.addons.connector.connector import install_in_connector


    install_in_connector()

.. warning:: If you miss this line of code, your custom ConnectorUnit
             classes won't be used.


Create your custom Backend
==========================

The connector can support the synchronization with various Magento
versions.

Actually the supported versions are referenced in
``magentoerpconnect/backend.py``::

    import openerp.addons.connector.backend as backend

    magento = backend.Backend('magento')
    magento1700 = backend.Backend(parent=magento, version='1.7')

In the connector, we are able to link pieces of code to a specific
version of Magento. If I link a piece of code to ``magento1700``, it
will be executed only if my Magento's version is actually Magento 1.7.

``magento`` is the parent of ``magento1700``. When the latter has no
specific piece of code, it will execute the former's one.

As you want to change parts of code specifically to **your version** of
Magento, you need to:

* create your own backend version
* link your custom parts of code with your own backend version (we'll
  cover this later)

Let's create our own backend, in ``customize_example/backend.py``::

    # -*- coding: utf-8 -*-
    import openerp.addons.connector.backend as backend
    import openerp.addons.magentoerpconnect.backend as magento_backend

    magento_myversion = backend.Backend(parent=magento_backend.magento1700,
                                        version='1.7-myversion')

And in ``customize_example/magento_model.py``::

    # -*- coding: utf-8 -*-
    from openerp import models, api


    class MagentoBackend(models.Model):
        _inherit = 'magento.backend'

        @api.model
        def select_versions(self):
            """ Available versions in the backend.

            Can be inherited to add custom versions.
            """
            versions = super(MagentoBackend, self).select_versions()
            versions.append(('1.7-myversion', '1.7 - My Version'))
            return versions

Things to note:

* The ``parent`` argument of my version is the 1.7 version. You have to
  set the correct parent according to your Magento version. If your
  Magento version does not exist, take the nearest version.
* the version should be the same in the ``backend.Backend`` and the
  model.
* We add the version in the model ``magento.backend`` so we'll be able to
  select it from the Odoo front-end.
* Do not forget to add the new python modules in ``__init__.py``.

Use it in Odoo
==============

Great, you now have the minimal stuff required to customize your
connector. When you create your backend in Odoo (menu ``Connectors >
Magento > Backends``), you have now to select **1.7 - My Version**.

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

The mappings of the fields are defined in subclasses of
:py:class:`connector.unit.mapper.ImportMapper` or
:py:class:`connector.unit.mapper.ExportMapper`, respectively
for the imports and the exports.

See the documentation about :py:class:`~connector.unit.mapper.Mapper`.

.. note:: The connector almost never works with the Odoo Models
          directly. Instead, it works with its own models, which
          ``_inherits`` (note the final ``s``) the base models. For
          instance, the Magento model for ``res.partner`` is
          ``magento.res.partner``. That's why you'll see
          ``magento.res.partner`` below.

          More details in `Magento Models`_.

When you need to change the mappings, you'll need to dive in the
``magentoerpconnect``'s code and locate the class which does this job for
your model. You won't change anything in this class, but you'll extend
it so you need to have a look on it.  For example, the mapping for
``magento.res.partner`` in ``magentoerpconnect`` is the following
(excerpt)::

  @magento
  class PartnerImportMapper(ImportMapper):
      _model_name = 'magento.res.partner'

      direct = [('email', 'email'),
                ('dob', 'birthday'),
                ('created_at', 'created_at'),
                ('updated_at', 'updated_at'),
                ('email', 'emailid'),
                ('taxvat', 'taxvat'),
                ('group_id', 'group_id'),
                ]

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

      [...snip...]

Here we can see 2 types of mappings:

* ``direct`` mappings, a field in Magento is directly written in the
  Odoo field. The Magento field is on the left, the Odoo one is on
  the right.
* methods decorated with ``@mapping``, when the mapping is more complex
  and need to apply some logic. The name of the methods is meaningless.
  They should return a ``dict`` with the field(s) to update and their
  values. A ``None`` return value will be ignored.
* the ``record`` argument receives the Magento record.

.. note:: This is not covered here, but for the ``ExportMapper``, an
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

* ``openerp_id``: ``Many2one`` to the ``res.partner`` (``_inherits``)
* ``backend_id``: ``Many2one`` to the ``magento.backend`` model (Magento
  Instance), for the partner this is a ``related`` because we already
  have a link to the website, itself associated to a ``magento.backend``.
* ``website_id``: ``Many2one`` to the ``magento.website`` model
* ``magento_id``: the ID of the customer on Magento
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
``customize_example/partner.py`` (I willingly skip the part 'add them in
the views')::

  # -*- coding: utf-8 -*-
  from openerp import models, fields

  class MagentoResPartner(models.Model):
      _inherit = 'magento.res.partner'

      created_in = fields.Char(string='Created In', readonly=True)


In the same file, I add the import of the Magento Backend to use and the
current mapper::

  from openerp.addons.magentoerpconnect.partner import PartnerImportMapper
  from .backend import magento_myversion

And I extend the partner's mapper, decorated with
``@magento_myversion``::

  @magento_myversion
  class MyPartnerImportMapper(PartnerImportMapper):
      _model_name = 'magento.res.partner'

      direct = PartnerImportMapper.direct + [('created_in', 'created_in')]

And that's it! The field will be imported along with the other fields.

.. attention:: Verify that you have selected the right version when you
               have created your backend in ``Connectors > Magento > Backends``
               otherwise your code will not be used.

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

In ``customize_example/partner.py``, I write::

  # -*- coding: utf-8 -*-
  from openerp import models, fields

  class ResPartner(models.Model):
      _inherit = 'res.partner'

      gender = fields.Selection(selection=[('male', 'Male'),
                                           ('female', 'Female')],
                                string='Gender')

The same imports than in the `Example 1.`_ are needed, but we need to
import ``mapping`` too::

  from openerp.addons.connector.unit.mapper import mapping
  from openerp.addons.magentoerpconnect.partner import PartnerImportMapper
  from .backend import magento_myversion

This is not a `direct` mapping, I will use a method to define the
``gender`` value::

  MAGENTO_GENDER = {'123': 'male',
                    '124': 'female'}

  @magento_myversion
  class MyPartnerImportMapper(PartnerImportMapper):
      _model_name = 'magento.res.partner'

      @mapping
      def gender(self, record):
          gender = MAGENTO_GENDER.get(record.get('gender'))
          return {'gender': gender}

The ``gender`` field will now be imported.

And now?
========

With theses principles, you should now be able to extend the original
mappings and add your own ones. This is applicable for the customers but
for any other model actually imported as well.
