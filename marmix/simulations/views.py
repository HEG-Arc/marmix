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
import io
import datetime

# Core Django imports
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from django.views.generic.edit import FormView, CreateView, UpdateView, DeleteView
from django.views.generic import View
from django.core.urlresolvers import reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from django.shortcuts import render_to_response, get_object_or_404, render
from django.template.context import RequestContext
from django.http import Http404, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.http import Http404
from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.utils.translation import ugettext_lazy as _
from django.forms.models import modelform_factory
from django.http import HttpResponseRedirect


# Third-party app imports
from rest_framework import permissions, viewsets
from xlsxwriter.workbook import Workbook

# MarMix imports
from .models import Simulation, Currency, Team
from .serializers import SimulationSerializer, CurrencySerializer, TeamSerializer
from .forms import TeamsSelectionForm, TeamJoinForm
from .tasks import initialize_simulation
from customers.models import Customer
from tickers.models import Ticker
from stocks.models import Stock
from .permissions import IsOwnerOrReadOnly, IsAdminOrReadOnly

logger = logging.getLogger(__name__)


def remove_tz_from_date(date):
    naive_date = datetime.datetime(date.year, date.month, date.day, date.hour, date.minute, date.second, date.microsecond)
    return naive_date


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
        context['simulation_state'] = Simulation.SIMULATION_STATE_DICT
        context['teams'] = Team.objects.filter(simulations=self.kwargs['pk']).select_related('user')
        return context

    def get_object(self, queryset=None):
        if self.request.user.is_staff:
            simulation = get_object_or_404(Simulation, pk=self.kwargs['pk'])
        else:
            simulation = get_object_or_404(Simulation, user=self.request.user, pk=self.kwargs['pk'])
        return simulation


class TeamsSelectionView(SuccessMessageMixin, FormView):
    template_name = 'simulations/manage_teams_form.html'
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

    def delete(self, request, *args, **kwargs):
        simulation = get_object_or_404(Simulation, pk=self.kwargs['pk'])
        messages.success(self.request, self.success_message % {'code': simulation.code, })
        return super(SimulationDelete, self).delete(request, *args, **kwargs)

    def get_object(self, queryset=None):
        if self.request.user.is_staff:
            simulation = get_object_or_404(Simulation, pk=self.kwargs['pk'])
        else:
            simulation = get_object_or_404(Simulation, user=self.request.user, pk=self.kwargs['pk'])
        return simulation


class TeamJoinView(SuccessMessageMixin, FormView):
    template_name = 'simulations/join_team_form.html'
    form_class = TeamJoinForm
    success_message = _("You were successfully added to the team <b>%(team_name)s</b>!")
    team_name = ''

    def form_valid(self, form):
        # This method is called when valid form data has been POSTed.
        # It should return an HttpResponse.
        team = get_object_or_404(Team, uuid=form.cleaned_data.get('uuid'))
        user = self.request.user
        team.users.add(user)
        self.team_name = team.name
        return super(TeamJoinView, self).form_valid(form)

    def get_success_url(self):
        return reverse('users:detail', kwargs={"username": self.request.user.username})

    def get_success_message(self, cleaned_data):
        return self.success_message % {'team_name': self.team_name, }


class TeamDetailView(DetailView):

    model = Team

    def get_context_data(self, **kwargs):
        context = super(TeamDetailView, self).get_context_data(**kwargs)
        #context['foo'] = "bar"
        return context

    def get_object(self, queryset=None):
        if self.request.user.is_staff:
            team = get_object_or_404(Team, pk=self.kwargs['pk'])
        else:
            team = get_object_or_404(Team, users=self.request.user, pk=self.kwargs['pk'])
        return team


def teams_export_xlsx(request, simulation_id=None, customer_id=None):
    if simulation_id:
        simulation = get_object_or_404(Simulation, pk=simulation_id)
        teams = simulation.teams.all()
    elif customer_id:
        customer = get_object_or_404(Customer, pk=customer_id)
        teams = Team.objects.all().filter(customer=customer)
    else:
        customers = Customer.objects.all().filter(users=request.user)
        teams = Team.objects.all().filter(customer=customers)

    output = io.BytesIO()
    workbook = Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet('Teams')
    bold = workbook.add_format({'bold': True})
    date_format = workbook.add_format({'num_format': 'yyyy-MM-dd'})
    worksheet.write(0, 0, 'Team', bold)
    worksheet.write(0, 1, 'Registration key', bold)
    worksheet.write(0, 2, 'Type', bold)
    worksheet.write(0, 3, '# Members', bold)
    worksheet.write(0, 4, 'Locked', bold)
    worksheet.write(0, 5, 'Created', bold)
    worksheet.write(0, 6, 'Modified', bold)
    worksheet.write(0, 7, 'Organization', bold)
    row = 1
    for team in teams:
        worksheet.write(row, 0, team.name)
        worksheet.write(row, 1, team.uuid)
        worksheet.write(row, 2, team.get_team_type_display())
        worksheet.write(row, 3, team.get_members)
        worksheet.write(row, 4, team.locked)
        worksheet.write(row, 5, remove_tz_from_date(team.created), date_format)
        worksheet.write(row, 6, remove_tz_from_date(team.modified), date_format)
        worksheet.write(row, 7, team.customer.name)
        row += 1
    workbook.close()

    output.seek(0)

    response = HttpResponse(output.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response['Content-Disposition'] = "attachment; filename=marmix_teams.xlsx"

    return response


class SimulationInitializeView(SuccessMessageMixin, UpdateView):
    """
    Update/Create the simulation. It calls initialize_simulation after form validation.
    """
    model = Ticker
    fields = ['nb_companies', 'initial_value', 'fixed_interest_rate']
    success_message = _("The simulation <b>%(code)s</b> was successfully initialized. You can play the simulation right now!")
    simulation = None

    def get_object(self, queryset=None):
        self.simulation = get_object_or_404(Simulation, pk=self.kwargs['pk'])
        try:
            ticker = self.simulation.ticker
        except Ticker.DoesNotExist:
            ticker = Ticker(simulation=self.simulation)
            ticker.save()
        return ticker

    def get_context_data(self, **kwargs):
        context = super(SimulationInitializeView, self).get_context_data(**kwargs)
        context['simulation_id'] = self.simulation.id
        return context

    def form_valid(self, form):
        simulation = self.simulation
        if simulation.simulation_type == Simulation.ADVANCED:
            form.instance.with_drift = True
        form.instance.simulation = simulation
        form.instance.user = self.request.user
        simulation.state = Simulation.READY
        simulation.save()
        # .apply_async([args,], queue='xxx', countdown=NN)
        initialize_simulation.apply_async([simulation])
        return super(SimulationInitializeView, self).form_valid(form)

    def get_success_url(self):
        return reverse('simulations-detail-view', kwargs={'pk': self.simulation.id})

    def get_success_message(self, cleaned_data):
        return self.success_message % {'code': self.object.simulation.code, }

    def get_form_class(self):
        fields = ['nb_rounds', 'nb_days', 'day_duration']
        if self.simulation.simulation_type == Simulation.INTRO:
            fields += ['nb_companies', 'initial_value', 'fixed_interest_rate']
        elif self.simulation.simulation_type == Simulation.ADVANCED:
            fields += ['nb_companies', 'initial_value', 'dividend_payoff_rate', 'transaction_costs', 'interest_rate', 'fixed_interest_rate']
        return modelform_factory(model=Ticker, fields=fields)


class MarketView(View):

    def get(self, request, *args, **kwargs):
        team = self.request.user.get_team
        simulation = get_object_or_404(Simulation, pk=team.current_simulation_id)
        return render(request, 'simulations/market.html', {'simulation': simulation, })


def manage_simulation(request, simulation_id, next_state):
    """
    Helper to change the current state of the simulation.

    Available states are READY -> RUNNING <-> PAUSED -> FINISHED -> ARCHIVED.

    :param request:
    :param simulation_id:
    :param next_state:
    :return: HttpResponseRedirect
    """
    simulation = get_object_or_404(Simulation, pk=simulation_id)
    next_state = int(next_state)
    if next_state == Simulation.RUNNING and simulation.state == Simulation.READY:
        simulation.state = Simulation.RUNNING
    elif next_state == Simulation.PAUSED and simulation.state == Simulation.RUNNING:
        simulation.state = Simulation.PAUSED
    elif next_state == Simulation.RUNNING and simulation.state == Simulation.PAUSED:
        simulation.state = Simulation.RUNNING
    elif next_state == Simulation.ARCHIVED and simulation.state == Simulation.FINISHED:
        simulation.state = Simulation.ARCHIVED
    simulation.save()
    messages.info(request, 'The simulation is now <b>%s</b>' % simulation.get_state_display())
    return HttpResponseRedirect(reverse('simulations-detail-view', args=[simulation.id]))