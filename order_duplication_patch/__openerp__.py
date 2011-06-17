#########################################################################
#                                                                       #
# Copyright (C) 2011 Openlabs Technologies & Consulting (P) Ltd.        #
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
    "name" : "Order Duplication Patch for Magento ERP Connector",
    "version" : "1.0",
    "depends" : ["base",
                 "magentoerpconnect"
                ],
    "author" : "Openlabs Technologies & Consulting (P) Ltd.",
    "description": """Magento may send orders in a random order which may ulimately lead to order duplication
""",
    "website" : "http://openlabs.co.in/blog/post/open-erp-magento-integration-new/",
    "category" : "Generic Modules",
    "init_xml" : [],
    "demo_xml" : [],
    "update_xml" : [],
    "active": False,
    "installable": True,

}

