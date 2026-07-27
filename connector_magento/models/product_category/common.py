# Copyright 2013-2019 Camptocamp SA
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import xmlrpc.client

from odoo import fields, models

from odoo.addons.component.core import Component
from odoo.addons.connector.exception import IDMissingInBackend

from ...components.backend_adapter import MAGENTO_DATETIME_FORMAT

_logger = logging.getLogger(__name__)


class MagentoProductCategory(models.Model):
    _name = "magento.product.category"
    _inherit = "magento.binding"
    _inherits = {"product.category": "odoo_id"}
    _description = "Magento Product Category"

    odoo_id = fields.Many2one(
        comodel_name="product.category",
        string="Product Category",
        required=True,
        ondelete="cascade",
    )
    description = fields.Text(translate=True)
    magento_parent_id = fields.Many2one(
        comodel_name="magento.product.category",
        string="Magento Parent Category",
        ondelete="cascade",
    )
    magento_child_ids = fields.One2many(
        comodel_name="magento.product.category",
        inverse_name="magento_parent_id",
        string="Magento Child Categories",
    )


class ProductCategory(models.Model):
    _inherit = "product.category"

    magento_bind_ids = fields.One2many(
        comodel_name="magento.product.category",
        inverse_name="odoo_id",
        string="Magento Bindings",
    )


class ProductCategoryAdapter(Component):
    _name = "magento.product.category.adapter"
    _inherit = "magento.adapter"
    _apply_on = "magento.product.category"

    _magento_model = "catalog_category"
    _magento2_model = "categories"
    _magento2_key = "id"
    _admin_path = "/{model}/index/"
    # Not valid without security key
    # _admin2_path = '/catalog/category/index/'

    def _call(self, method, arguments, http_method=None, storeview=None):
        try:
            return super()._call(
                method, arguments, http_method=http_method, storeview=storeview
            )
        except xmlrpc.client.Fault as err:
            # 101 is the error in the Magento API
            # when the category does not exist
            if err.faultCode == 102:
                raise IDMissingInBackend from err
            else:
                raise

    def search(self, filters=None, from_date=None, to_date=None):
        """Search records according to some criteria and return a
        list of ids

        :rtype: list
        """
        if filters is None:
            filters = {}

        dt_fmt = MAGENTO_DATETIME_FORMAT
        if from_date is not None:
            filters.setdefault("updated_at", {})
            # updated_at include the created records
            filters["updated_at"]["from"] = from_date.strftime(dt_fmt)
        if to_date is not None:
            filters.setdefault("updated_at", {})
            filters["updated_at"]["to"] = to_date.strftime(dt_fmt)
        if self.collection.version and self.collection.version.startswith("1."):
            return self._call(
                "oerp_catalog_category.search", [filters] if filters else [{}]
            )
        return super().search(filters=filters)

    def read(self, external_id, storeview_id=None, attributes=None):
        """Returns the information of a record

        :rtype: dict
        """
        # pylint: disable=method-required-super
        if self.collection.version and self.collection.version.startswith("1."):
            return self._call(
                f"{self._magento_model}.info",
                [int(external_id), storeview_id, attributes],
            )
        return super().read(external_id, attributes, storeview=storeview_id)

    def tree(self, parent_id=None, storeview_id=None):
        """Returns a tree of product categories

        :rtype: dict
        """

        def filter_ids(tree):
            children = {}
            if isinstance(tree, dict) and tree.get("children"):
                for node in tree["children"]:
                    children.update(filter_ids(node))
            categ_id = tree.get("category_id") if isinstance(tree, dict) else None
            return {categ_id: children} if categ_id else children

        def filter_ids_m2(node):
            children = {}
            if isinstance(node, dict) and node.get("children_data"):
                for child in node["children_data"]:
                    children.update(filter_ids_m2(child))
            node_id = node.get("id") if isinstance(node, dict) else None
            return {node_id: children} if node_id else children

        if self.collection.version and str(self.collection.version).startswith("1."):
            args = []
            if parent_id:
                args.append(int(parent_id))
            if storeview_id:
                args.append(storeview_id)
            tree = self._call(f"{self._magento_model}.tree", args)
            return filter_ids(tree)
        else:
            res = self._call("categories", None)
            return filter_ids_m2(res) if isinstance(res, dict) else {}

    def move(self, categ_id, parent_id, after_categ_id=None):
        if self.collection.version and self.collection.version.startswith("1."):
            return self._call(
                f"{self._magento_model}.move", [categ_id, parent_id, after_categ_id]
            )
        return self._call(
            f"{self._magento2_model}/{categ_id}/move",
            {
                "parent_id": parent_id,
                "after_id": after_categ_id,
            },
        )

    def get_assigned_product(self, categ_id):
        if self.collection.version and self.collection.version.startswith("1."):
            return self._call(f"{self._magento_model}.assignedProducts", [categ_id])
        raise NotImplementedError  # TODO

    def assign_product(self, categ_id, product_id, position=0):
        if self.collection.version and self.collection.version.startswith("1."):
            return self._call(
                f"{self._magento_model}.assignProduct",
                [categ_id, product_id, position, "id"],
            )
        raise NotImplementedError  # TODO

    def update_product(self, categ_id, product_id, position=0):
        if self.collection.version and self.collection.version.startswith("1."):
            return self._call(
                f"{self._magento_model}.updateProduct",
                [categ_id, product_id, position, "id"],
            )
        raise NotImplementedError  # TODO

    def remove_product(self, categ_id, product_id):
        if self.collection.version and self.collection.version.startswith("1."):
            return self._call(
                f"{self._magento_model}.removeProduct", [categ_id, product_id, "id"]
            )
        raise NotImplementedError  # TODO
