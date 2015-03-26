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
import collections

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
from django.utils.decorators import method_decorator
from django.db.models import Sum, Count


# Third-party app imports
from rest_framework import permissions, viewsets, status, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated


# MarMix imports
from .models import Stock, Quote, Order, TransactionLine, dividends_list
from .serializers import StockSerializer, QuoteSerializer, OrderSerializer, CreateOrderSerializer, NestedStockSerializer
from .filters import QuoteFilter
from simulations.models import current_sim_day, current_holdings

logger = logging.getLogger(__name__)


class StockListView(ListView):

    model = Stock

    def get_context_data(self, **kwargs):
        context = super(StockListView, self).get_context_data(**kwargs)
        #context['foo'] = "bar"
        return context

    def get_queryset(self):
        if self.request.user.is_staff:
            stocks = Stock.objects.all()
        else:
            stocks = Stock.objects.all().filter(simulation_id=self.request.user.get_team.current_simulation_id)
        return stocks


class StockDetailView(DetailView):

    model = Stock

    def get_context_data(self, **kwargs):
        context = super(StockDetailView, self).get_context_data(**kwargs)
        #context['foo'] = "bar"
        return context


class HoldingsView(View):

    def get(self, request, *args, **kwargs):
        team = self.request.user.get_team
        orders = Order.objects.all().filter(stock__simulation_id=team.current_simulation_id).filter(team=team).select_related('stock', 'transaction')
        clock = current_sim_day(team.current_simulation_id)
        return render(request, 'stocks/transactionline_list.html', {'orders': orders, 'team': team, 'clock': clock})


class DividendsView(View):

    def get(self, request, *args, **kwargs):
        team = self.request.user.get_team
        tl = TransactionLine.objects.select_related('stock', 'transaction').filter(transaction__simulation_id=team.current_simulation_id).filter(
            team_id=team.id).filter(asset_type=TransactionLine.DIVIDENDS).order_by('-transaction__sim_round', 'stock__symbol')
        clock = current_sim_day(team.current_simulation_id)
        return render(request, 'stocks/dividends_list.html', {'transactions': tl, 'clock': clock})


class OrderListView(ListView):

    model = Order

    def get_context_data(self, **kwargs):
        context = super(OrderListView, self).get_context_data(**kwargs)
        #context['foo'] = "bar"
        return context


class StockViewSet(viewsets.ModelViewSet):
    serializer_class = StockSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        """
        This view should return a list of all the stocks for the simulation of the authenticated user.
        """
        user = self.request.user
        return Stock.objects.filter(simulation_id=user.get_team.current_simulation_id)


class MarketViewSet(viewsets.ModelViewSet):
    serializer_class = NestedStockSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        """
        This view should return a list of all the stocks for the simulation of the authenticated user.
        """
        user = self.request.user
        return Stock.objects.filter(simulation_id=user.get_team.current_simulation_id)

class QuoteViewSet(viewsets.ModelViewSet):
    queryset = Quote.objects.all()
    serializer_class = QuoteSerializer
    permission_classes = (permissions.IsAuthenticated,)
    filter_class = QuoteFilter
    ordering_fields = ('-timestamp')


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        """
        This view should return a list of all the orders for the authenticated user.
        """
        user = self.request.user
        team = user.get_team
        return Order.objects.filter(stock__simulation_id=team.current_simulation_id).filter(team_id=user.get_team.id).order_by('-created_at')


class CreateOrderViewSet(viewsets.ModelViewSet):
    serializer_class = CreateOrderSerializer
    permission_classes = (permissions.IsAuthenticated,)

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(CreateOrderViewSet, self).dispatch(*args, **kwargs)

    def get_queryset(self):
        """
        This view should return a list of all the orders for the authenticated user.
        """
        user = self.request.user
        return Order.objects.filter(team=user.get_team)

    def perform_create(self, serializer):
        serializer.save(team=self.request.user.get_team)


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

    def get_form(self, form_class):
        form = super(OrderCreateView, self).get_form(form_class)
        form.fields['stock'].queryset = Stock.objects.filter(simulation_id=self.request.user.get_team.current_simulation_id)
        return form


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


class HoldingsViewSet(viewsets.ViewSet):
    """
    Current portfolio of the request.user.
    """
    permission_classes = (IsAuthenticated, )

    def list(self, request, *args, **kwargs):
        trader = request.user.get_team
        holdings = current_holdings(trader.id, trader.current_simulation_id)
        response = Response(holdings, status=status.HTTP_200_OK)
        return response


class DividendsViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated,)

    def list(self, request, *args, **kwargs):
        team = request.user.get_team
        dividends = dividends_list(team.id)
        response = Response(dividends, status=status.HTTP_200_OK)
        return response


class OrderBookViewSet(viewsets.ViewSet):

    def retrieve(self, request, pk=None):
        stock = get_object_or_404(Stock, pk=pk)
        orders = Order.objects.filter(stock=stock, state=Order.SUBMITTED, price__gt=0).values('price',
                                      'order_type').annotate(qty=Sum('quantity'), orders=Count('id')).order_by('-price')
        current_price = stock.price
        order_book = []
        last_order_price = None
        for order in orders:
            if not last_order_price:
                last_order_price = order['price']
                if current_price > last_order_price:
                    order_book.append({'price': current_price, 'quantity': 0, 'orders': 0, 'order_type': 'MARKET'})
            if last_order_price > current_price > order['price']:
                order_book.append({'price': current_price, 'quantity': 0, 'orders': 0, 'order_type': 'MARKET'})
            order_book.append({'price': order['price'], 'quantity': order['qty'], 'orders': order['orders'], 'order_type': order['order_type']})
            last_order_price = order['price']
        if last_order_price > current_price:
            order_book.append({'price': current_price, 'quantity': 0, 'orders': 0, 'order_type': 'MARKET'})
        response = Response(order_book, status=status.HTTP_200_OK)
        return response