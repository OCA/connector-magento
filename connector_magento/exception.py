# © 2013 Guewen Baconnier,Camptocamp SA,Akretion
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp.addons.connector.exception import RetryableJobError


class OrderImportRuleRetry(RetryableJobError):
    """ The sale order import will be retried later. """
