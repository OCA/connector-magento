# -*- coding: utf-8 -*-
# © 2013 Guewen Baconnier,Camptocamp SA,Akretion
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from datetime import datetime

import odoo
from odoo.addons.component.core import AbstractComponent
from .backend_adapter import MAGENTO_DATETIME_FORMAT

_logger = logging.getLogger(__name__)


"""

Exporters for Magento.

In addition to its export job, an exporter has to:

* check in Magento if the record has been updated more recently than the
  last sync date and if yes, delay an import
* call the ``bind`` method of the binder to update the last sync date

"""


class MagentoBaseExporter(AbstractComponent):
    """ Base exporter for Magento """

    _name = 'magento.base.exporter'
    _inherit = ['generic.exporter', 'base.magento.connector']
    _usage = 'record.exporter'
    _default_binding_fields = 'magento_bind_ids'

    def _should_import(self):
        """ Before the export, compare the update date
        in Magento and the last sync date in Odoo,
        if the former is more recent, schedule an import
        to not miss changes done in Magento.
        """
        assert self.binding
        if not self.external_id:
            return False
        sync = self.binding.sync_date
        if not sync:
            return True
        record = self.backend_adapter.read(self.external_id,
                                           attributes=['updated_at'])
        if not record['updated_at']:
            # in rare case it can be empty, in doubt, import it
            return True
        sync_date = odoo.fields.Datetime.from_string(sync)
        magento_date = datetime.strptime(record['updated_at'],
                                         MAGENTO_DATETIME_FORMAT)
        return sync_date < magento_date


class MagentoExporter(AbstractComponent):
    """ A common flow for the exports to Magento """

    _name = 'magento.exporter'
    _inherit = 'magento.base.exporter'
