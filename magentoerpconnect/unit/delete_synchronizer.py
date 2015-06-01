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

from openerp.tools.translate import _
from openerp.addons.connector.queue.job import job, related_action
from openerp.addons.connector.unit.synchronizer import Deleter
from ..connector import get_environment
from ..related_action import link


class MagentoDeleter(Deleter):
    """ Base deleter for Magento """

    def run(self, magento_id):
        """ Run the synchronization, delete the record on Magento

        :param magento_id: identifier of the record to delete
        """
        self.backend_adapter.delete(magento_id)
        return _('Record %s deleted on Magento') % magento_id


MagentoDeleteSynchronizer = MagentoDeleter  # deprecated


@job(default_channel='root.magento')
@related_action(action=link)
def export_delete_record(session, model_name, backend_id, magento_id):
    """ Delete a record on Magento """
    env = get_environment(session, model_name, backend_id)
    deleter = env.get_connector_unit(MagentoDeleter)
    return deleter.run(magento_id)
