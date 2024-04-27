# © 2013 Guewen Baconnier,Camptocamp SA,Akretion
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.component.core import AbstractComponent
from odoo.addons.connector.components.mapper import mapping


class MagentoImportMapper(AbstractComponent):
    _name = 'magento.import.mapper'
    _inherit = ['base.magento.connector', 'base.import.mapper']
    _usage = 'import.mapper'

    @mapping
    def user_data(self, record):
        return {f: record.get(f[3:]) for f in self.model._fields if f.startswith('x__')}


class MagentoExportMapper(AbstractComponent):
    _name = 'magento.export.mapper'
    _inherit = ['base.magento.connector', 'base.export.mapper']
    _usage = 'export.mapper'


def normalize_datetime(field):
    """Change a invalid date which comes from Magento, if
    no real date is set to null for correct import to
    OpenERP"""

    def modifier(self, record, to_attr):
        if record[field] == '0000-00-00 00:00:00':
            return None
        return record[field]
    return modifier
