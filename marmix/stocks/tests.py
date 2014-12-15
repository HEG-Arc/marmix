# -*- coding: UTF-8 -*-
# tests.py
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
from datetime import datetime, timedelta
import random, decimal

# Core Django imports
from django.test import TestCase
from django.core.urlresolvers import resolve
from django.http import HttpRequest
from django.template.loader import render_to_string

# Third-party app imports

# MarMix imports
from .models import Stock, Quote


class StocksViewsTest(TestCase):

    def setUp(self):
        self.first_stock = Stock.objects.create(symbol='AAAA', name='Stock A', quantity=1000, description='This is a <u>good</u> company!')
        self.second_stock = Stock.objects.create(symbol='BBBB', name='Stock B', quantity=9999)
        for i in range(0, 10):
            Quote.objects.create(stock=self.first_stock, price=decimal.Decimal(str(random.random()*10000000)), timestamp=datetime.now()+timedelta(minutes=i))

    def test_displays_all_stocks(self):
        response = self.client.get('/stocks/')

        self.assertContains(response, 'AAAA')
        self.assertContains(response, 'Stock A')
        self.assertContains(response, 'BBBB')
        self.assertContains(response, 'Stock B')

    def test_uses_list_template(self):
        response = self.client.get('/stocks/')
        self.assertTemplateUsed(response, 'stocks/stock_list.html')

    def test_display_one_stock(self):
        response = self.client.get('/stocks/%d/' % (self.first_stock.id,))

        self.assertContains(response, 'AAAA')
        self.assertContains(response, '1000')
        self.assertContains(response, '<u>good</u>')
        self.assertNotContains(response, 'BBBB')
        self.assertNotContains(response, '9999')

        response = self.client.get('/stocks/%d/' % (self.second_stock.id,))

        self.assertNotContains(response, 'AAAA')
        self.assertNotContains(response, '1000')
        self.assertContains(response, 'BBBB')
        self.assertContains(response, '9999')

    def test_uses_detail_template(self):
        response = self.client.get('/stocks/%d/' % (self.first_stock.id,))
        self.assertTemplateUsed(response, 'stocks/stock_detail.html')