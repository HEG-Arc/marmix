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
import datetime

# Core Django imports
from django.utils import timezone

# Third-party app imports
from rest_framework import serializers

# MarMix imports
from .models import TickerCompany, CompanyShare, CompanyFinancial
from simulations.models import current_sim_day
from stocks.serializers import NestedStockSerializer


class NestedSharesSerializer(serializers.ModelSerializer):

    class Meta:
        model = CompanyShare
        fields = ('id', 'share_value', 'dividends', 'net_income', 'drift', 'sim_round')


class NestedFinancialsSerializer(serializers.ModelSerializer):

    class Meta:
        model = CompanyFinancial
        fields = ('id', 'daily_dividend', 'daily_net_income', 'sim_round', 'sim_day')


class CompaniesSerializer(serializers.ModelSerializer):
    shares = serializers.SerializerMethodField()
    financials = serializers.SerializerMethodField()
    stock = NestedStockSerializer(many=False, read_only=True)

    class Meta:
        model = TickerCompany
        fields = ('id', 'ticker', 'symbol', 'name', 'stock', 'description', 'shares', 'financials')

    def get_shares(self, obj):
        clock = current_sim_day(obj.ticker.simulation_id)
        if clock['sim_round'] == 0:
            round = 1
        else:
            round = clock['sim_round']
        current_shares = CompanyShare.objects.filter(company=obj).filter(sim_round__lt=round).filter(sim_round__gt=0)
        serializer = NestedSharesSerializer(current_shares, many=True)
        return serializer.data

    def get_financials(self, obj):
        clock = current_sim_day(obj.ticker.simulation_id)
        current_financials = CompanyFinancial.objects.filter(company=obj).filter(sim_date__lte=clock['sim_round']*100+clock['sim_day']).filter(sim_round__gt=0).filter(sim_day__gt=0)
        serializer = NestedFinancialsSerializer(current_financials, many=True)
        return serializer.data

