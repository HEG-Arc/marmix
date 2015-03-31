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
from .views import SimulationDetailView, SimulationListView, TeamsSelectionView, SimulationCreate, SimulationUpdate, \
    SimulationDelete, TeamJoinView, TeamDetailView, teams_export_xlsx, SimulationInitializeView, manage_simulation, \
    MarketView, SimulationInfoUpdate

urlpatterns = patterns('',
    url(r'^(?P<pk>\d+)/select-teams/$', TeamsSelectionView.as_view(), name='teams-selection-view'),
    url(r'^(?P<pk>\d+)/$', SimulationDetailView.as_view(), name='simulations-detail-view'),
    url(r'^add/(?P<customer_id>\d+)/$', SimulationCreate.as_view(), name='simulation-add-view'),
    url(r'^(?P<pk>\d+)/update/info/$', SimulationInfoUpdate.as_view(), name='simulation-info-update-view'),
    url(r'^(?P<pk>\d+)/update/$', SimulationUpdate.as_view(), name='simulation-update-view'),
    url(r'^(?P<pk>\d+)/delete/$', SimulationDelete.as_view(), name='simulation-delete-view'),
    url(r'^(?P<pk>\d+)/initialize/$', SimulationInitializeView.as_view(), name='simulation-initialize-view'),
    url(r'^(?P<simulation_id>\d+)/state/(?P<next_state>\d+)/$', manage_simulation, name='simulation-manage-state'),
    url(r'^join-team/$', TeamJoinView.as_view(), name='team-join-view'),
    url(r'^team/(?P<pk>\d+)/$', TeamDetailView.as_view(), name='team-detail-view'),
    url(r'^(?P<simulation_id>\d+)/teams/export/$', teams_export_xlsx, name='teams-export-xlsx-simulation'),
    url(r'^teams/export/(?P<customer_id>\d+)/$', teams_export_xlsx, name='teams-export-xlsx-customer'),
    url(r'^teams/export/$', teams_export_xlsx, name='teams-export-xlsx'),
    url(r'market/$', MarketView.as_view(), name='market-view'),
    url(r'^', SimulationListView.as_view(), name='simulations-list-view'),
)