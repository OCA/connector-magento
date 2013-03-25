.. _tutorial-customize:


######################################
Tutorial: customization in sub-modules
######################################

This tutorial will explain how you can customize several parts of the
connector in your own OpenERP module. It assumes that you already have
some knowledge in the OpenERP development. You can still refer to the
`official OpenERP documentation`_.


.. contents:: Sections:
   :local:
   :backlinks: top


.. _official OpenERP documentation: http://doc.openerp.com/trunk/developers/server/

***************************************
Bootstrap your own customization module
***************************************

You should never make changes in the official modules, instead, you need
to create your own module and apply your personalizations from there.

As an example, throughout this tutorial, we'll create our own
customization module, we'll name it, in a very original manner,
`customize`.

Common OpenERP files
====================

A `magentoerpconnect` customization module is like any OpenERP module,
so you will first need to create the **manifest** `customize/__openerp__.py`:

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
    =================

    Explain what this module changes.
    """,
     'data': [],
     'installable': True,
     'application': False,
    }

Nothing special but 2 things to note:

* It depends from `magentoerpconnect`.
* The module category should preferably be `Connector`.

Of course, you also need to create the `__init__.py` file where you will
put the imports of your python modules.

Create your custom Backend
==========================

The connector can support the synchronization with various Magento
versions.

Actually the supported versions are referenced in
`magentoerpconnect/backend.py`::

    import openerp.addons.connector.backend as backend

    magento = backend.Backend('magento')
    magento1700 = backend.Backend(parent=magento, version='1.7')

In the above example, `magento` means Magento *globally*. The parts of
code in the connector are linked with `magento`, but parts specific to
the version 1.7 are linked with `magento1700`.

As you want to change parts of code specifically to **your version** of
Magento, you need to:

* create your own backend version
* link your custom parts of code with your own backend version (we'll
  cover this later)

Let's create our own backend, in `customize/backend.py`::

    # -*- coding: utf-8 -*-
    import openerp.addons.connector.backend as backend
    import openerp.addons.magentoerpconnect.backend as magento_backend

    magento_myversion = backend.Backend(parent=magento_backend.magento1700,
                                        version='1.7-myversion')

And in `customize/magento_model.py`::

    # -*- coding: utf-8 -*-
    from openerp.osv import orm


    class magento_backend(orm.Model):
        _inherit = 'magento.backend'

        def _select_versions(self, cr, uid, context=None):
            """ Available versions

            Can be inherited to add custom versions.
            """
            versions = super(magento_backend, self)._select_versions(cr, uid, context=context)
            versions.append(('1.7-myversion', '1.7 - My Version'))
            return versions

        _columns = {
            'version': fields.selection(_select_versions, string='Version', required=True),
            }

Things to note:

* The `parent` of my version is the 1.7 version. You have to set the
  correct parent according to your Magento version. If your Magento
  version does not exist, take the nearest version.
* We add the version in the model `magento.backend` so we'll be able to
  select it from the OpenERP front-end.
* Do not forget to add the new python modules in `__init__.py`.

Use it in OpenERP
=================

Great, you now have the minimal stuff required to customize your
connector. When you create your backend in OpenERP (menu `Connectors >
Magento > Backends`), you should now select **1.7 - My Version**.

In the next chapter, we'll cover the most common personalization:
`Adding mappings of fields`_.


*************************
Adding mappings of fields
*************************

The mappings of the fields define how they are linked between OpenERP and Magento.

To be able to customize the mappings, you need to already have a
customization module, if that's not already done, you can go through the
previous chapter: `Bootstrap your own customization module`_.




