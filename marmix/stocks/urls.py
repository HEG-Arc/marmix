# -*- coding: UTF-8 -*-
# urls.py
#
# Copyright (C) 2014 HES-SO//HEG Arc
#
# Author(s): Cédric Gaspoz <cedric.gaspoz@he-arc.ch>
#
# This file is part of MarMix.
#
# MarMix is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# MarMix is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with MarMix. If not, see <http://www.gnu.org/licenses/>.

# Stdlib imports

# Core Django imports
from django.conf.urls import patterns, url

# Third-party app imports

# MarMix imports
from .views import StockListView, StockDetailView, HoldingsView, OrderCreateView, OrderUpdateView, OrderListView, OrderDeleteView, DividendsView

urlpatterns = patterns('',
    url(r'^(?P<pk>\d+)/$', StockDetailView.as_view(), name='stocks-detail-view'),
    url(r'^holdings/$', HoldingsView.as_view(), name='holdings-list-view'),
    url(r'^dividends/$', DividendsView.as_view(), name='dividends-list-view'),
    url(r'^order/(?P<pk>\d+)/update/$', OrderUpdateView.as_view(), name='order-update-view'),
    url(r'^order/(?P<pk>\d+)/delete/$', OrderDeleteView.as_view(), name='order-delete-view'),
    url(r'^order/new/$', OrderCreateView.as_view(), name='order-create-view'),
    url(r'^order/$', OrderListView.as_view(), name='orders-list-view'),
    url(r'^$', StockListView.as_view(), name='stocks-list-view'),
)