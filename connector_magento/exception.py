# © 2013 Guewen Baconnier,Camptocamp SA,Akretion
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp.addons.connector.exception import RetryableJobError


class OrderImportRuleRetry(RetryableJobError):
    """ The sale order import will be retried later. """


class MagentoError(Exception):
    """Catch Json Error
    Attributes:
        json -- Catching the json error explanation of the failed job
    """

    def __init__(self, msg, json):
        super().__init__(msg)
        self.json = json
