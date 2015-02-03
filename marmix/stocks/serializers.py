# -*- coding: UTF-8 -*-
# serializers.py
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

# Third-party app imports
from rest_framework import serializers

# MarMix imports
from .models import Stock, Quote, Order, HistoricalPrice
from simulations.models import stock_historical_prices


class NestedHistoricalPrice(serializers.ModelSerializer):
    class Meta:
        model = HistoricalPrice
        fields = ('id', 'sim_round', 'sim_day', 'price_open', 'price_high', 'price_low', 'price_close', 'volume')


class NestedOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ('order_type', 'quantity', 'price', 'created_at', 'sim_round', 'sim_day', 'transaction')


class StockSerializer(serializers.ModelSerializer):
    orders = serializers.SerializerMethodField()
    history = serializers.SerializerMethodField()

    class Meta:
        model = Stock
        fields = ('id', 'simulation', 'symbol', 'name', 'description', 'quantity', 'price', 'orders', 'history')

    def get_orders(self, obj):
        open_orders = Order.objects.filter(stock=obj, price__isnull=False, transaction__isnull=True)
        serializer = NestedOrderSerializer(open_orders, many=True)
        return serializer.data

    def get_history(self, obj):
        history = stock_historical_prices(obj.id)
        serializer = NestedHistoricalPrice(history, many=True)
        return serializer.data


class QuoteSerializer(serializers.ModelSerializer):

    class Meta:
        model = Quote
        fields = ('id', 'stock', 'price', 'timestamp', 'sim_round', 'sim_day')


class OrderSerializer(serializers.ModelSerializer):

    class Meta:
        model = Order
        fields = ('id', 'stock', 'team', 'order_type', 'quantity', 'price', 'created_at', 'sim_round', 'sim_day', 'transaction')