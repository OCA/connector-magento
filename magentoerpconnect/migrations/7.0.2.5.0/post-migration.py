# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Ondřej Kuzník
#    Copyright 2014 credativ, ltd.
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

import logging

logger = logging.getLogger('upgrade')


def migrate(cr, version):
    """
    The tax inclusion setting has moved from the backend to the storeview.
    """
    if version:  # do not run on a fresh DB, see lp:1259975
        logger.info("Migrating magentoerpconnect from version %s", version)
        cr.execute("UPDATE magento_storeview msw "
                   "SET catalog_price_tax_included = "
                   "    (SELECT mb.catalog_price_tax_included "
                   "            FROM magento_backend mb WHERE "
                   "                mb.id = msw.backend_id)")
        cr.execute("ALTER TABLE magento_backend DROP "
                   "      COLUMN catalog_price_tax_included")
