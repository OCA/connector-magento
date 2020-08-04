# Copyright 2013-2019 Camptocamp SA
# © 2016 Sodexis
# © 2020 Glodo UK
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping


class ProductExportMapper(Component):
    _name = "magento.product.product.export.mapper"
    _inherit = "magento.export.mapper"
    _apply_on = ["magento.product.product"]

    # TODO: name mapping doesnt seem to work
    direct = [
        ("name", "name"),
        ("default_code", "sku"),
        ("product_type", "type_id"),
    ]

    @mapping
    def price(self, record):
        # magento currency id
        currency_id = self.backend_record.default_currency

        price = record.list_price or 0.0

        if record.currency_id != currency_id:
            price = record.currency_id._convert(
                price, currency_id, self.env.user.company_id, fields.Datetime.now(),
            )

        return {"price": price}

    @mapping
    def weight(self, record):
        return {"weight": record.weight or 0.0}

    @mapping
    def is_active(self, record):
        """Link the status field.
        status == 1 in Magento means active.
        Magento 2.x needs an integer, 1.x a string """
        if self.collection.version == "1.7":
            return {"status": ("1" if record.active else "0")}
        return {"status": (1 if record.active else 0)}

    @mapping
    def custom_attributes(self, record):
        if self.collection.version == "1.7":
            # No support for <2.0 right now.
            raise NotImplementedError

        # Categories
        binder = self.binder_for("magento.product.category")

        categories = []

        if record.categ_id.magento_bind_ids:
            categories.append(binder.to_external(record.categ_id.magento_bind_ids))

        extra_categories = record.categ_ids
        for cat in extra_categories:
            if cat.magento_bind_ids:
                categories.append(binder.to_external(cat.magento_bind_ids))
        # End Categories

        # Full obj to return
        return {
            "custom_attributes": [
                {"attribute_code": "description", "value": record.description,},
                {
                    "attribute_code": "short_description",
                    "value": record.description_sale,
                },
                {"attribute_code": "category_ids", "value": categories,},
                {"attribute_code": "cost", "value": record.standard_price or 0.0,},
            ],
        }


class ProductInventoryExporter(Component):
    _name = "magento.product.product.exporter"
    _inherit = "magento.exporter"
    _apply_on = ["magento.product.product"]
    _usage = "product.inventory.exporter"

    _map_backorders = {
        "use_default": 0,
        "no": 0,
        "yes": 1,
        "yes-and-notification": 2,
    }

    def _get_data(self, binding, fields):
        result = {}
        if "magento_qty" in fields:
            result.update(
                {
                    "qty": binding.magento_qty,
                    # put the stock availability to "out of stock"
                    "is_in_stock": int(binding.magento_qty > 0),
                }
            )
        if "manage_stock" in fields:
            manage = binding.manage_stock
            result.update(
                {
                    "manage_stock": int(manage == "yes"),
                    "use_config_manage_stock": int(manage == "use_default"),
                }
            )
        if "backorders" in fields:
            backorders = binding.backorders
            result.update(
                {
                    "backorders": self._map_backorders[backorders],
                    "use_config_backorders": int(backorders == "use_default"),
                }
            )
        return result

    def run(self, binding, fields):
        """ Export the product inventory to Magento """
        external_id = self.binder.to_external(binding)
        data = self._get_data(binding, fields)

        mapper = self.component(usage="export.mapper")
        content_data = mapper.map_record(binding).values()

        content_data.update(
            {"attribute_set_id": self.backend_record.default_attribute_set,}
        )

        if not external_id:
            # create
            res = self.backend_adapter.create(binding.default_code, content_data)

            if not res or not res.get("id", False):
                raise Exception("No data back from Magento products create call")

            binding.external_id = res.get("sku")
            binding.magento_internal_id = res.get("id")
        else:
            # update
            self.backend_adapter.write(
                external_id, content_data
            )  # if non-inventory fields changed
            self.backend_adapter.update_inventory(
                external_id, data
            )  # just inventory fields change
