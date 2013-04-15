# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2013 Camptocamp SA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from functools import wraps
from openerp.osv import orm
from openerp.addons.connector.event import (on_record_write,
                                            on_record_create,
                                            on_record_unlink
                                            )
import openerp.addons.magentoerpconnect.consumer as magentoerpconnect


class magentoerpconnect_installed(orm.AbstractModel):
    """Empty model used to know if the module is installed on the
    database.

    If the model is in the registry, the module is installed.
    """
    _name = 'magentoerpconnect_pricing.installed'


def magento_pricing_consumer(func):
    """ Use this decorator on all the consumers of
    magentoerpconnect_pricing.

    It will prevent the consumers from being fired when the addon is not
    installed.
    """
    @wraps(func)
    def wrapped(*args, **kwargs):
        session = args[0]
        if session.pool.get('magentoerpconnect_pricing.installed'):
            return func(*args, **kwargs)
    return wrapped
