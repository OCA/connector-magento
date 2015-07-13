# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2013 Camptocamp SA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

# flake8: noqa : ignore style in this file because it is a data file
# only

"""
Magento responses for calls done by the connector.

This set of responses has been recorded for the synchronizations
with a Magento 1.7 version with demo data.

It has been recorded using ``magentoerpconnect.unit.backend_adapter.record``
and ``magentoerpconnect.unit.backend_adapter.output_recorder``

This set of data contains examples of imported products.
"""

# a simple product with images
simple_product_and_images = {
    ('ol_catalog_product.info', (122, None, None, 'id')): {'categories': ['1'],
                                                        'color': '60',
                                                        'cost': '2.0000',
                                                        'country_of_manufacture': None,
                                                        'created_at': '2007-08-24 19:53:06',
                                                        'custom_design': '',
                                                        'custom_design_from': None,
                                                        'custom_design_to': None,
                                                        'custom_layout_update': '',
                                                        'description': "We bought these with the intention of making shirts for our family reunion, only to come back the next day to find each and every one of them had been tagged by The Bear.  Oh well -- can't argue with art.  Now you can make your grandparents proud by wearing an original piece of graf work to YOUR family reunion!",
                                                        'enable_googlecheckout': '0',
                                                        'gender': '35',
                                                        'gift_message_available': '',
                                                        'group_price': [],
                                                        'has_options': '0',
                                                        'image_label': None,
                                                        'is_recurring': '0',
                                                        'manufacturer': None,
                                                        'meta_description': 'Ink Eater: Krylon Bombear Destroyed Tee',
                                                        'meta_keyword': 'Ink Eater: Krylon Bombear Destroyed Tee',
                                                        'meta_title': 'Ink Eater: Krylon Bombear Destroyed Tee',
                                                        'minimal_price': '22.0000',
                                                        'model': 'Ink Eater:',
                                                        'msrp': None,
                                                        'msrp_display_actual_price_type': '4',
                                                        'msrp_enabled': '2',
                                                        'name': 'Ink Eater: Krylon Bombear Destroyed Tee',
                                                        'news_from_date': None,
                                                        'news_to_date': None,
                                                        'old_id': None,
                                                        'options_container': 'container2',
                                                        'page_layout': None,
                                                        'price': '22.0000',
                                                        'product_id': '122',
                                                        'recurring_profile': None,
                                                        'required_options': '0',
                                                        'set': '41',
                                                        'shirt_size': '98',
                                                        'short_description': "We bought these with the intention of making shirts for our family reunion, only to come back the next day to find each and every one of them had been tagged by The Bear.  Oh well -- can't argue with art.  Now you can make your grandparents proud by wearing an original piece of graf work to YOUR family reunion!",
                                                        'sku': 'ink_lrg',
                                                        'small_image_label': None,
                                                        'special_from_date': None,
                                                        'special_price': None,
                                                        'special_to_date': None,
                                                        'status': '1',
                                                        'tax_class_id': '2',
                                                        'thumbnail_label': None,
                                                        'tier_price': [],
                                                        'type': 'simple',
                                                        'type_id': 'simple',
                                                        'updated_at': '2013-09-02 08:01:34',
                                                        'url_key': 'ink-eater-krylon-bombear-destroyed-tee-lrg',
                                                        'url_path': 'ink-eater-krylon-bombear-destroyed-tee-lrg.html',
                                                        'visibility': '1',
                                                        'websites': ['1'],
                                                        'weight': '0.5000'},
    ('product_media.list', (122, None, 'id')): [{'exclude': '1',
                                                 'file': '/i/n/ink-eater-krylon-bombear-destroyed-tee-2.jpg',
                                                 'label': '',
                                                 'position': '0',
                                                 'types': ['thumbnail'],
                                                 'url': 'http://localhost:9100/media/catalog/product/i/n/ink-eater-krylon-bombear-destroyed-tee-2.jpg'},
                                                {'exclude': '0',
                                                 'file': '/i/n/ink-eater-krylon-bombear-destroyed-tee-1.jpg',
                                                 'label': '',
                                                 'position': '3',
                                                 'types': ['small_image'],
                                                 'url': 'http://localhost:9100/media/catalog/product/i/n/ink-eater-krylon-bombear-destroyed-tee-1.jpg'},
                                                {'exclude': '0',
                                                 'file': '/m/a/magentoerpconnect_1.png',
                                                 'label': '',
                                                 'position': '4',
                                                 'types': [],
                                                 'url': 'http://localhost:9100/media/catalog/product/m/a/magentoerpconnect_1.png'}],
}
