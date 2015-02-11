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
import logging
from decimal import Decimal

# Core Django imports
from django.views.generic.list import ListView
from django.shortcuts import render_to_response, get_object_or_404
from django.forms.formsets import formset_factory
from django.shortcuts import redirect

# Third-party app imports
from rest_framework import permissions, viewsets

# MarMix imports
from .models import TickerCompany, CompanyShare, CompanyShareForm
from .serializers import CompaniesSerializer
from .tasks import prepare_dividends_payments, set_closing_price
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


class CompaniesViewSet(viewsets.ModelViewSet):
    serializer_class = CompaniesSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        """
        This view should return a list of all the companies for the authenticated user.
        """
        return TickerCompany.objects.filter(ticker__simulation_id=self.request.user.get_team.current_simulation_id)


def CompanyShareCreateView(request, simulation_id, sim_round):
    simulation = Simulation.objects.get(pk=simulation_id)
    sim_round = int(sim_round)
    initial = []
    for stock in simulation.stocks.all():
        initial.append({'company': stock.symbol})
    CompanyShareFormset = formset_factory(CompanyShareForm)
    if request.method == 'POST':
        formset = CompanyShareFormset(request.POST, request.FILES)
        if formset.is_valid():
            for form in formset:
                if form.cleaned_data.get('company'):
                    company = TickerCompany.objects.get(symbol=form.cleaned_data['company'], ticker=simulation.ticker)
                    net_income = form.cleaned_data['net_income']
                    dividends = net_income * simulation.ticker.dividend_payoff_rate / 100 / company.stock.quantity
                    if dividends < 0:
                        dividends = 0
                    if sim_round - 2 > 0:
                        past = CompanyShare.objects.get(company=company, sim_round=sim_round - 2)
                        drift = Decimal(net_income) / past.net_income - 1
                        try:
                            share_value = dividends * (1 + drift) / (Decimal(0.1) - drift)
                        except:
                            share_value = 0
                    else:
                        share_value = 0
                        drift = 0
                    share = CompanyShare(company=company, share_value=share_value, dividends=dividends, net_income=net_income, drift=drift, sim_round=sim_round - 1)
                    share.save()
            prepare_dividends_payments.apply_async([simulation.id, sim_round-1])
        return redirect('simulations-detail-view', simulation.id)
    else:
        formset = CompanyShareFormset(initial=initial)
    return render_to_response('tickers/company_shares_create.html', {'formset': formset, 'sim_round': sim_round, 'simulation_id': simulation_id})


def closes_market(request, simulation_id):
    set_closing_price(simulation_id)
    return redirect('market-view')