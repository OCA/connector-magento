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
    Rename magento.stock.picking.out to magento.stock.picking
    """
    if version:  # do not run on a fresh DB, see lp:1259975
        logger.info("Migrating magentoerpconnect from version %s", version)

        old = 'magento_stock_picking_out'
        new = 'magento_stock_picking'
        logger.info("model %s: renaming to %s", old, new)
        cr.execute("ALTER TABLE %s RENAME TO %s" % (old, new))
        cr.execute("ALTER SEQUENCE %s_id_seq RENAME TO %s_id_seq" % (old, new))
        cr.execute('UPDATE ir_model SET model = %s '
                   'WHERE model = %s', (new, old,))
        cr.execute('UPDATE ir_model_fields SET relation = %s '
                   'WHERE relation = %s', (new, old,))
        cr.execute('UPDATE ir_model_data SET model = %s '
                   'WHERE model = %s', (new, old,))
        cr.execute('ALTER INDEX %s_pkey RENAME to %s_fkey' % (old, new))
        # the constraint will be created again on update
        cr.execute('ALTER TABLE %s DROP CONSTRAINT '
                   '%s_magento_uniq' % (new, old))
