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
from django.views.generic.edit import FormView, CreateView, UpdateView, DeleteView
from django.core.urlresolvers import reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from django.shortcuts import render_to_response, get_object_or_404
from django.template.context import RequestContext
from django.http import Http404, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.http import Http404
from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.utils.translation import ugettext_lazy as _

# Third-party app imports
from rest_framework import permissions, viewsets

# MarMix imports
from .models import Simulation, Currency, Team
from .serializers import SimulationSerializer, CurrencySerializer, TeamSerializer
from .forms import TeamsSelectionForm
from billing.models import Customer
from .permissions import IsOwnerOrReadOnly, IsAdminOrReadOnly

logger = logging.getLogger(__name__)


class SimulationViewSet(viewsets.ModelViewSet):
    queryset = Simulation.objects.all()
    serializer_class = SimulationSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CurrencyViewSet(viewsets.ModelViewSet):
    queryset = Currency.objects.all()
    serializer_class = CurrencySerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)


class TeamViewSet(viewsets.ModelViewSet):
    queryset = Team.objects.all()
    serializer_class = TeamSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)


class SimulationListView(ListView):

    model = Simulation

    def get_context_data(self, **kwargs):
        context = super(SimulationListView, self).get_context_data(**kwargs)
        #context['foo'] = "bar"
        return context

    def get_queryset(self):
        if self.request.user.is_staff:
            simulations = Simulation.objects.all()
        else:
            simulations = Simulation.objects.all().filter(user=self.request.user)
        return simulations


class SimulationDetailView(DetailView):

    model = Simulation

    def get_context_data(self, **kwargs):
        context = super(SimulationDetailView, self).get_context_data(**kwargs)
        #context['foo'] = "bar"
        return context

    def get_object(self, queryset=None):
        if self.request.user.is_staff:
            simulation = get_object_or_404(Simulation, pk=self.kwargs['pk'])
        else:
            simulation = get_object_or_404(Simulation, user=self.request.user, pk=self.kwargs['pk'])
        return simulation


class TeamsSelectionView(SuccessMessageMixin, FormView):
    template_name = 'simulation/manage_teams_form.html'
    form_class = TeamsSelectionForm
    success_message = _("Participating teams were successfully updated")

    def form_valid(self, form):
        # This method is called when valid form data has been POSTed.
        # It should return an HttpResponse.
        simulation = get_object_or_404(Simulation, pk=self.kwargs['pk'])
        selected_teams = form.cleaned_data.get('teams')
        all_teams = Team.objects.all().filter(customer=simulation.customer)
        for team in all_teams:
            if team in selected_teams:
                # Add to simulation
                team.simulations.add(simulation)
            else:
                team.simulations.remove(simulation)
        return super(TeamsSelectionView, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(TeamsSelectionView, self).get_context_data(**kwargs)
        simulation = get_object_or_404(Simulation, pk=self.kwargs['pk'])
        context['simulation_id'] = simulation.id
        return context

    def get_success_url(self):
        return reverse('simulations-detail-view', kwargs={'pk': self.kwargs['pk']})

    def get_form_kwargs(self):
        kwargs = super(TeamsSelectionView, self).get_form_kwargs()
        simulation = get_object_or_404(Simulation, pk=self.kwargs['pk'])
        kwargs['customer'] = simulation.customer
        kwargs['simulation'] = simulation
        return kwargs


class SimulationCreate(SuccessMessageMixin, CreateView):
    model = Simulation
    fields = ['code', 'simulation_type', 'capital', 'currency']
    success_message = _("The simulation <b>%(code)s</b> was successfully created. You can start using it right now!")

    def get_context_data(self, **kwargs):
        context = super(SimulationCreate, self).get_context_data(**kwargs)
        customer = get_object_or_404(Customer, pk=self.kwargs['customer_id'])
        context['customer_id'] = customer.id
        context['action'] = 'create'
        return context

    def form_valid(self, form):
        form.instance.customer = get_object_or_404(Customer, pk=self.kwargs['customer_id'])
        form.instance.user = self.request.user
        return super(SimulationCreate, self).form_valid(form)

    def get_success_url(self):
        return reverse('simulations-detail-view', kwargs={'pk': self.object.pk})

    def get_success_message(self, cleaned_data):
        return self.success_message % {'code': self.object.code, }


class SimulationUpdate(SuccessMessageMixin, UpdateView):
    model = Simulation
    fields = ['code', 'simulation_type', 'capital', 'currency']
    success_message = _("The simulation was successfully updated!")

    def get_success_url(self):
        return reverse('simulations-detail-view', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super(SimulationUpdate, self).get_context_data(**kwargs)
        simulation = get_object_or_404(Simulation, pk=self.kwargs['pk'])
        context['simulation_id'] = simulation.id
        context['action'] = 'update'
        return context

    def get_object(self, queryset=None):
        if self.request.user.is_staff:
            simulation = get_object_or_404(Simulation, pk=self.kwargs['pk'])
        else:
            simulation = get_object_or_404(Simulation, user=self.request.user, pk=self.kwargs['pk'])
        return simulation


class SimulationDelete(SuccessMessageMixin, DeleteView):
    model = Simulation
    success_url = reverse_lazy('simulations-list-view')
    success_message = _("The simulation <b>%(code)s</b> was successfully deleted!")

    def get_success_message(self, cleaned_data):
        return self.success_message % {'code': self.object.code, }

    def get_object(self, queryset=None):
        if self.request.user.is_staff:
            simulation = get_object_or_404(Simulation, pk=self.kwargs['pk'])
        else:
            simulation = get_object_or_404(Simulation, user=self.request.user, pk=self.kwargs['pk'])
        return simulation