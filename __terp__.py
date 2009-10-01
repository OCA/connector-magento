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
    "depends" : ["base","product","product_m2mcategories","sale"],
    "author" : "Sharoon Thomas",
    "description": """Magento E-commerce management using Open ERP.
    Inspired by the original work of Raphael Valyi, my mentor & friend.
""",
    "website" : "http://www.openlabs.co.in/magentoerpconnect",
    "category" : "Generic Modules",
    "init_xml" : [],
    "demo_xml" : [],
    "update_xml" : [
            'magerp_core_view.xml',
            'magerp_product_view.xml',
            'magerp_customer_view.xml',
            'magerp_menu.xml',
                    ],
    "active": False,
    "installable": True,

}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

