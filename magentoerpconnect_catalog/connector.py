# -*- coding: utf-8 -*-

from openerp.osv import orm


class magentoerpconnect_export_partner_installed(orm.AbstractModel):
    """Empty model used to know if the module is installed on the
    database.

    If the model is in the registry, the module is installed.
    """
    _name = 'magentoerpconnect_catalog.installed'