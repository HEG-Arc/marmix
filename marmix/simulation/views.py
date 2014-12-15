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
from django.http import Http404

# Third-party app imports
from rest_framework import permissions, viewsets

# MarMix imports
from .models import Simulation, Currency
from .serializers import SimulationSerializer, CurrencySerializer
from .permissions import IsOwnerOrReadOnly, IsAdminOrReadOnly

logger = logging.getLogger(__name__)


class SimulationViewSet(viewsets.ModelViewSet):
    queryset = Simulation.objects.all()
    serializer_class = SimulationSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly,)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CurrencyViewSet(viewsets.ModelViewSet):
    queryset = Currency.objects.all()
    serializer_class = CurrencySerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)


# class FooDetailView(DetailView):
#
#     model = <model>
#
#     def get_context_data(self, **kwargs):
#         context = super(FooDetailView, self).get_context_data(**kwargs)
#         context['foo'] = "bar"
#         return context


# class FooListView(ListView):
#
#     model = <model>
#
#     def get_context_data(self, **kwargs):
#         context = super(FooListView, self).get_context_data(**kwargs)
#         context['foo'] = "bar"
#         return context