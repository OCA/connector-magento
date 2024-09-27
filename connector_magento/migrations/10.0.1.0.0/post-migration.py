# -*- coding: utf-8 -*-
# (c) 2021 Hunki Enterprises BV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


def migrate(cr, version=None):
    """Migrate jobs to new format"""
    if not version:
        return
    # import_record
    cr.execute(
        """update queue_job
        set
        args=json_build_array(
            json_build_object(
                '_type', 'odoo_recordset',
                'model', 'magento.backend',
                'ids', array[args::json->1],
                'uid', user_id
            ),
            args::json->2
        )
        where
        method_name=%s and model_name in %s""",
        ('import_record', tuple([
            'magento.account.invoice',
            'magento.sale.order',
            'magento.sale.order.line',
            'magento.stock.picking',
        ])),
    )
    # sale_order_import_batch
    cr.execute(
        """update queue_job
        set
        method_name='import_batch',
        args=json_build_array(
            json_build_object(
                '_type', 'odoo_recordset',
                'model', 'magento.backend',
                'ids', array[args::json->1],
                'uid', user_id
            )
        )
        where
        method_name=%s and model_name in %s""",
        ('sale_order_import_batch', tuple([
            'magento.sale.order',
        ])),
    )
    # export_picking_done
    cr.execute(
        """update queue_job
        set
        record_ids=json_build_array(
            args::json->1
        ),
        args=json_build_array()
        where
        method_name=%s and model_name in %s""",
        ('export_picking_done', tuple([
            'magento.stock.picking',
        ])),
    )
    # export_tracking_number
    cr.execute(
        """update queue_job
        set
        record_ids=json_build_array(
            args::json->1
        ),
        args=json_build_array()
        where
        method_name=%s and model_name in %s""",
        ('export_tracking_number', tuple([
            'magento.stock.picking',
        ])),
    )
