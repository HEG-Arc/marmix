# -*- coding: UTF-8 -*-
# views.py
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
from hashlib import sha256
import json
import logging

# Core Django imports
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from django.shortcuts import render_to_response, get_object_or_404
from django.template.context import RequestContext
from django.http import Http404, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

# Third-party app imports

# MarMix imports
from .models import TickerCompany
from simulations.models import Simulation


logger = logging.getLogger(__name__)


class CompaniesView(ListView):

    model = TickerCompany
    template_name = 'tickers/companies.html'

    def get_context_data(self, **kwargs):
        context = super(CompaniesView, self).get_context_data(**kwargs)
        context['simulation'] = Simulation.objects.get(pk=self.request.user.get_team.current_simulation_id)
        return context

    def get_queryset(self):
        return TickerCompany.objects.filter(ticker__simulation_id=self.request.user.get_team.current_simulation_id)


# class FooListView(ListView):
#
#     model = <model>
#
#     def get_context_data(self, **kwargs):
#         context = super(FooListView, self).get_context_data(**kwargs)
#         context['foo'] = "bar"
#         return context