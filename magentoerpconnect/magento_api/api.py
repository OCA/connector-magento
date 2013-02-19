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

"""
Extend the magento lib with new API entry points.
"""

from magento.api import API


class Website(API):
    """
    Website API

    Example usage::

        with Website(url, username, password) as api:
            return api.list()

    """
    __slots__ = ()

    def list(self, filters=None):
        """
        Retrieve list of websites

        :param filters: filters
        :type filters: dict
        :return: List of dictionaries of matching records
        :rtype: list
        """
        return self.call('ol_websites.list', filters and [filters] or [{}])

    def info(self, id, filters=None):
        """
        Retrieve list of websites

        :param filters: filters
        :type filters: dict
        :return: List of dictionaries of matching records
        :rtype: list
        """
        return self.call('ol_websites.info', [id])


class Store(API):
    """
    Store API

    Example usage::

        with Store(url, username, password) as api:
            return api.list()

    """
    __slots__ = ()

    def list(self, filters=None):
        """
        Retrieve list of stores

        :param filters: filters
        :type filters: dict
        :return: List of dictionaries of matching records
        :rtype: list
        """
        return self.call('ol_groups.list', filters and [filters] or [{}])

    def info(self, id, filters=None):
        """
        Retreive list of saleshops

        :param filters: filters
        :type filters: dict
        :return: List of dictionaries of matching records
        :rtype: list
        """
        return self.call('ol_groups.info', [id])


class StoreView(API):
    """
    StoreView API

    Example usage::

        with StoreView(url, username, password) as api:
            return api.list()

    """
    __slots__ = ()

    def list(self, filters=None):
        """
        Retrieve list of storeviews

        :param filters: filters
        :type filters: dict
        :return: List of dictionaries of matching records
        :rtype: list
        """
        return self.call('ol_storeviews.list', filters and [filters] or [{}])

    def info(self, id, filters=None):
        """
        Retrieve list of storeviews

        :param filters: filters
        :type filters: dict
        :return: List of dictionaries of matching records
        :rtype: list
        """
        return self.call('ol_storeviews.info', [id])

