# coding: utf-8
# Copyright 2021 Opener B.V.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)
import logging
try:
    from openupgradelib import openupgrade
except ImportError:
    openupgrade = None


def migrate(cr, version):
    """
    Rename columns openerp_id -> odoo_id and magento_id -> external_id
    """
    if not version:
        return
    logger = logging.getLogger("odoo.addons.connector_magento.migrations")
    if openupgrade is None:
        logger.error(
            "Openupgradelib is not available, so we will not rename the "
            "magento_id columns to external_id on the binding models.")
        return
    for table in [
        "magento_account_invoice",
        "magento_address",
        "magento_binding_backend_read",
        "magento_product_category",
        "magento_product_product",
        "magento_res_partner",
        "magento_res_partner_category",
        "magento_sale_order",
        "magento_sale_order_line",
        "magento_stock_picking",
        "magento_store",
        "magento_storeview",
        "magento_warehouse",
        "magento_website",
    ]:
        if not openupgrade.table_exists(cr, table):
            logger.warn("Table %s was not found", table)
            continue
        for old, new in [
                ("magento_id", "external_id"), ("openerp_id", "odoo_id")]:
            if not openupgrade.column_exists(cr, table, old):
                logger.debug("Column %s.%s was not found", table, old)
                continue
            if openupgrade.column_exists(cr, table, new):
                logger.debug("Column %s.%s already exists", table, new)
                continue
            openupgrade.rename_columns(cr, {table: [(old, new)]})
