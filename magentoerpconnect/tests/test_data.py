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

magento_base_responses = {
    ('ol_groups.info', ('0', None)): {'default_store_id': '0',
                                      'group_id': '0',
                                      'name': 'Default',
                                      'root_category_id': '0',
                                      'website_id': '0'},
    ('ol_groups.info', ('1', None)): {'default_store_id': '1',
                                      'group_id': '1',
                                      'name': 'Main Store',
                                      'root_category_id': '3',
                                      'website_id': '1'},
    ('ol_groups.info', ('2', None)): {'default_store_id': '4',
                                      'group_id': '2',
                                      'name': 'Russian',
                                      'root_category_id': '3',
                                      'website_id': '1'},
    ('ol_groups.search', (frozenset([]),)): ['0', '1', '2'],
    ('ol_storeviews.info', ('0', None)): {'code': 'admin',
                                          'group_id': '0',
                                          'is_active': '1',
                                          'name': 'Admin',
                                          'sort_order': '0',
                                          'store_id': '0',
                                          'website_id': '0'},
    ('ol_storeviews.info', ('1', None)): {'code': 'default',
                                          'group_id': '1',
                                          'is_active': '1',
                                          'name': 'English',
                                          'sort_order': '1',
                                          'store_id': '1',
                                          'website_id': '1'},
    ('ol_storeviews.info', ('2', None)): {'code': 'german',
                                          'group_id': '1',
                                          'is_active': '1',
                                          'name': 'German',
                                          'sort_order': '3',
                                          'store_id': '2',
                                          'website_id': '1'},
    ('ol_storeviews.info', ('3', None)): {'code': 'french',
                                          'group_id': '1',
                                          'is_active': '1',
                                          'name': 'French',
                                          'sort_order': '2',
                                          'store_id': '3',
                                          'website_id': '1'},
    ('ol_storeviews.info', ('4', None)): {'code': 'russian',
                                          'group_id': '2',
                                          'is_active': '1',
                                          'name': 'Russian',
                                          'sort_order': '5',
                                          'store_id': '4',
                                          'website_id': '1'},
('ol_storeviews.search', (frozenset([]),)): ['0', '1', '2', '3', '4'],
('ol_websites.info', ('0', None)): {'code': 'admin',
                                    'default_group_id': '0',
                                    'is_default': '0',
                                    'name': 'Admin',
                                    'sort_order': '0',
                                    'website_id': '0'},
('ol_websites.info', ('1', None)): {'code': 'base',
                                    'default_group_id': '1',
                                    'is_default': '1',
                                    'name': 'Main Website',
                                    'sort_order': '0',
                                    'website_id': '1'},
('ol_websites.search', (frozenset([]),)): ['0', '1']
}
