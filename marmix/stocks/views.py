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
from django.views.generic import View
from django.contrib.messages.views import SuccessMessageMixin
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse, reverse_lazy
from django.shortcuts import render_to_response, get_object_or_404, render
from django.template.context import RequestContext
from django.http import Http404, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.contrib import messages


# Third-party app imports
from rest_framework import permissions, viewsets

# MarMix imports
from .models import Stock, Quote, Order, TransactionLine
from .serializers import StockSerializer, QuoteSerializer, OrderSerializer


logger = logging.getLogger(__name__)


class StockListView(ListView):

    model = Stock

    def get_context_data(self, **kwargs):
        context = super(StockListView, self).get_context_data(**kwargs)
        #context['foo'] = "bar"
        return context


class StockDetailView(DetailView):

    model = Stock

    def get_context_data(self, **kwargs):
        context = super(StockDetailView, self).get_context_data(**kwargs)
        #context['foo'] = "bar"
        return context


class HoldingsView(View):

    def get(self, request, *args, **kwargs):
        team = self.request.user.get_team
        orders = Order.objects.all().filter(team=team).select_related('stock', 'transaction')
        return render(request, 'stocks/transactionline_list.html', {'orders': orders, 'team': team})


class OrderListView(ListView):

    model = Order

    def get_context_data(self, **kwargs):
        context = super(OrderListView, self).get_context_data(**kwargs)
        #context['foo'] = "bar"
        return context


class StockViewSet(viewsets.ModelViewSet):
    queryset = Stock.objects.all()
    serializer_class = StockSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)


class QuoteViewSet(viewsets.ModelViewSet):
    queryset = Quote.objects.all()
    serializer_class = QuoteSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)


class OrderCreateView(SuccessMessageMixin, CreateView):
    model = Order
    fields = ['stock', 'order_type', 'quantity', 'price']
    success_message = _("Your order <b>%(order_id)s</b> is registered. It will be fulfilled when the next matching order is found.")

    def get_context_data(self, **kwargs):
        context = super(OrderCreateView, self).get_context_data(**kwargs)
        context['action'] = 'create'
        return context

    def form_valid(self, form):
        team = self.request.user.get_team
        form.instance.team = team
        return super(OrderCreateView, self).form_valid(form)

    def get_success_url(self):
        return reverse('holdings-list-view')

    def get_success_message(self, cleaned_data):
        return self.success_message % {'order_id': self.object.id, }


class OrderUpdateView(SuccessMessageMixin, UpdateView):
    model = Order
    fields = ['stock', 'order_type', 'quantity', 'price']
    success_message = _("Your order <b>%(order_id)s</b> is updated. It will be fulfilled when the next matching order is found.")

    def get_context_data(self, **kwargs):
        context = super(OrderUpdateView, self).get_context_data(**kwargs)
        context['action'] = 'update'
        context['order_id'] = self.object.id
        return context

    def form_valid(self, form):
        return super(OrderUpdateView, self).form_valid(form)

    def get_success_url(self):
        return reverse('holdings-list-view')

    def get_success_message(self, cleaned_data):
        return self.success_message % {'order_id': self.object.id, }


class OrderDeleteView(SuccessMessageMixin, DeleteView):
    model = Order
    success_url = reverse_lazy('holdings-list-view')
    success_message = _("The order <b>%(code)s</b> was successfully deleted!")

    def delete(self, request, *args, **kwargs):
        order = get_object_or_404(Order, pk=self.kwargs['pk'])
        messages.success(self.request, self.success_message % {'code': order.id, })
        return super(OrderDeleteView, self).delete(request, *args, **kwargs)