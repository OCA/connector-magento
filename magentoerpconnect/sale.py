# -*- coding: utf-8 -*-
#########################################################################
#                                                                       #
#########################################################################
#                                                                       #
# Copyright (C) 2011  Sharoon Thomas                                    #
# Copyright (C) 2009  Raphaël Valyi                                     #
# Copyright (C) 2011 Akretion Sébastien BEAU sebastien.beau@akretion.com#
# Copyright (C) 2011-2012 Camptocamp Guewen Baconnier                   #
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

from openerp.osv.orm import Model
from openerp.osv import fields
from openerp.osv.osv import except_osv
import netsvc
from tools.translate import _
from openerp import tools
import time
from tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.addons.connector.external_osv import ExternalSession
from openerp.addons.connector.decorator import only_for_referential, open_report

#from connector import report

import logging
_logger = logging.getLogger(__name__)

DEBUG = True
NOTRY = False

#TODO, may be move that on out CSV mapping, but not sure we can easily
#see OpenERP sale/sale.py and Magento app/code/core/Mage/Sales/Model/Order.php for details
ORDER_STATUS_MAPPING = {
    'manual': 'processing',
    'progress': 'processing',
    'shipping_except': 'complete',
    'invoice_except': 'complete',
    'done': 'complete',
    'cancel': 'canceled',
    'waiting_date': 'holded'}
SALE_ORDER_IMPORT_STEP = 200



