# -*- coding: utf-8 -*-
# © 2013 Guewen Baconnier,Camptocamp SA,Akretion
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

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
