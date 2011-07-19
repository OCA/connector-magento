#########################################################################
#                                                                       #
# Copyright (C) 2009  Sharoon Thomas                                    #
#                                                                       #
#This program is free software: you can redistribute it and/or modify   #
#it under the terms of the GNU General Public License as published by   #
#the Free Software Foundation, either version 3 of the License, or      #
#(at your option) any later version.                                    #
#                                                                       #
#This program is distributed in the hope that it will be useful,        #
#but WITHOUT ANY WARRANTY; without even the implied warranty of         #
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the          #
#GNU General Public License for more details.                           #
#                                                                       #
#You should have received a copy of the GNU General Public License      #
#along with this program.  If not, see <http://www.gnu.org/licenses/>.  #
#########################################################################
{
    "name" : "Magento e-commerce",
    "version" : "1.0",
    "depends" : ["base",
                 "product",
                 "product_m2mcategories",
                 'delivery',
                 "base_sale_multichannels",
                 "product_images_olbs",
                 "product_links",
                 "base_json_fields",
                ],
    "author" : "Sharoon Thomas, Raphael Valyi",
    "description": """Magento E-commerce management
""",
    "website" : "http://openlabs.co.in/blog/post/open-erp-magento-integration-new/",
    "category" : "Generic Modules",
    "init_xml" : [],
    "demo_xml" : [],
    "update_xml" : [
            'security/ir.model.access.csv',
            'settings/magerp.product_category_attribute_options.csv',
            'settings/external.referential.type.csv',
            'settings/external.mapping.template.csv',
            'settings/external.mappinglines.template.csv',
            'settings/magerp_product_product_type.xml',
            'magerp_data.xml',
            'magerp_core_view.xml',
            'product_view.xml',
            'partner_view.xml',
            'sale_view.xml',
            'product_images_view.xml',
            'magerp_menu.xml',
            'delivery_view.xml',
            'product_links_view.xml',
            'wizard/product_change_sku_view.xml',
                    ],
    "active": False,
    "installable": True,

}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

