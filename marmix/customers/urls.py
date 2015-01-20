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
from .views import CustomerListView, CustomerDetailView, TeamsCreateView


urlpatterns = patterns('',
    url(r'^(?P<pk>\d+)/create-teams$', TeamsCreateView.as_view(), name='teams-create-view'),
    url(r'^(?P<pk>\d+)/$', CustomerDetailView.as_view(), name='customers-detail-view'),
    url(r'^$', CustomerListView.as_view(), name='customers-list-view'),

#     url(r'^foo/$', foo, name='foo'),
)