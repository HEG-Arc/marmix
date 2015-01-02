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
from django.views.generic.edit import FormView
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import render_to_response, get_object_or_404
from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.template.context import RequestContext
from django.http import Http404, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings


# Third-party app imports

# MarMix imports
from .models import Customer
from .forms import TeamCreateForm


logger = logging.getLogger(__name__)


class CustomerDetailView(DetailView):

    def get_object(self, queryset=None):
        if self.request.user.is_staff:
            customer = get_object_or_404(Customer, pk=self.kwargs['pk'])
        else:
            customer = get_object_or_404(Customer, users=self.request.user, pk=self.kwargs['pk'])
        return customer

    def get_context_data(self, **kwargs):
        context = super(CustomerDetailView, self).get_context_data(**kwargs)
        context['foo'] = "bar"
        return context


class CustomerListView(ListView):

    def get_queryset(self):
        if self.request.user.is_staff:
            return Customer.objects.all()
        else:
            return Customer.objects.filter(users=self.request.user)

    def get_context_data(self, **kwargs):
        context = super(CustomerListView, self).get_context_data(**kwargs)
        context['foo'] = "bar"
        return context


class TeamsCreateView(SuccessMessageMixin, FormView):
    template_name = 'billing/create_teams.html'
    form_class = TeamCreateForm
    success_message = "%(qty)s teams were created successfully"

    def form_valid(self, form):
        # This method is called when valid form data has been POSTed.
        # It should return an HttpResponse.
        customer = get_object_or_404(Customer, pk=self.kwargs['pk'])
        success = form.create_teams(customer, self.request)
        if success:
            return super(TeamsCreateView, self).form_valid(form)
        else:
            return redirect('customers-detail-view', pk=self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        context = super(TeamsCreateView, self).get_context_data(**kwargs)
        customer = get_object_or_404(Customer, pk=self.kwargs['pk'])
        context['customer_id'] = customer.id
        return context

    def get_success_url(self):
        return reverse('customers-detail-view', kwargs={'pk': self.kwargs['pk']})

    def get_success_message(self, cleaned_data):
        return self.success_message % dict(cleaned_data,)