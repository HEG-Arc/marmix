# -*- coding: UTF-8 -*-
# models.py
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
from django.utils import timezone
# Core Django imports
from django.db import models
from django.utils.translation import ugettext_lazy as _

# Third-party app imports
from django_extensions.db.models import TimeStampedModel

# MarMix imports
from simulation.models import Simulation, Team


class Stock(TimeStampedModel):
    """
    Stocks are shares of a company that are automatically generated during the simulation setup.
    """
    simulation = models.ForeignKey(Simulation, verbose_name=_("simulation"), related_name="stocks", help_text=_("Related simulation"))
    symbol = models.CharField(verbose_name=_("symbol"), max_length=4, help_text=_("Symbol of the stock (4 chars)"))
    name = models.CharField(verbose_name=_("name"), max_length=100, help_text=_("Full name of the stock"))
    description = models.TextField(verbose_name=_("description"), blank=True, help_text=_("Description of the stock (HTML)"))
    quantity = models.IntegerField(verbose_name=_("quantity"), default=1, help_text=_("Total quantity of stocks in circulation"))

    class Meta:
        verbose_name = _('stock')
        verbose_name_plural = _('stocks')
        ordering = ['symbol']

    def __str__(self):
        return self.symbol


class Quote(models.Model):
    """
    Quotes are the price of a given stock at a certain time.
    """
    stock = models.ForeignKey('Stock', verbose_name=_("stock"), related_name="quotes", help_text=_("Related stock"))
    price = models.DecimalField(verbose_name=_("stock price"), max_digits=14, decimal_places=4,
                                          default='0.0000', help_text=_("Current stock price"))
    timestamp = models.DateTimeField(verbose_name=_("timestamp"), auto_now_add=True, help_text=_("Timestamp of the quote"))

    class Meta:
        verbose_name = _('quote')
        verbose_name_plural = _('quotes')
        ordering = ['-timestamp']

    def __str__(self):
        return "%s - %s (%s)" % (self.stock, self.price, self.timestamp)


class Order(models.Model):
    """
    Orders are made by teams and posted in the order book. They are then processed by the order manager.
    """
    BID = 'BID'
    ASK = 'ASK'
    SIMULATION_TYPE_CHOICES = (
        (BID, _('bid')),
        (ASK, _('ask')),
    )

    stock = models.ForeignKey('Stock', verbose_name=_("stock"), related_name="orders", help_text=_("Related stock"))
    team = models.ForeignKey(Team, verbose_name=_("team"), related_name="orders", help_text=_("Team which placed the order"))
    order_type = models.CharField(verbose_name=_("type of order"), max_length=5, choices=SIMULATION_TYPE_CHOICES,
                                  default=BID, help_text=_("The type of order (bid/ask)"))
    quantity = models.IntegerField(verbose_name=_("quantity ordered"), default=0, help_text=_("Quantity ordered. If the total quantity can not be provided, a new order will be created with the balance"))
    price = models.DecimalField(verbose_name=_("price tag"), max_digits=14, decimal_places=4,
                                blank=True, null=True, help_text=_("Price tag for one stock. If NULL, best available price"))
    created_at = models.DateTimeField(verbose_name=_("created"), auto_now_add=True, help_text=_("Creation of the order"))
    fulfilled_at = models.DateTimeField(verbose_name=_("fulfilled"), null=True, blank=True, help_text=_("Fulfillment of the order"))

    class Meta:
        verbose_name = _('order')
        verbose_name_plural = _('orders')
        ordering = ['stock', 'price']

    def __str__(self):
        if self.order_type == self.BID:
            quantity = -1 * self.quantity
        else:
            quantity = self.quantity
        return "%s: %s@%s" % (self.stock, quantity, self.price)


class Transaction(models.Model):
    """
    Transactions are the result of order placed that are fulfilled.
    """
    stock = models.ForeignKey('Stock', verbose_name=_("stock"), related_name="transactions", help_text=_("Related stock"))
    team_bid = models.ForeignKey(Team, verbose_name=_("buyers"), related_name="buy_transactions", help_text=_("Team buying the stock"))
    team_ask = models.ForeignKey(Team, verbose_name=_("sellers"), related_name="sell_transactions", help_text=_("Team selling the stock"))
    quantity = models.IntegerField(verbose_name=_("quantity"), default=0, help_text=_("Quantity exchanged"))
    price = models.DecimalField(verbose_name=_("price tag"), max_digits=14, decimal_places=4,
                                blank=True, null=True, help_text=_("Price tag for one stock"))
    fulfilled_at = models.DateTimeField(verbose_name=_("fulfilled"), auto_now_add=True, help_text=_("Fulfillment date"))

    class Meta:
        verbose_name = _('order')
        verbose_name_plural = _('orders')
        ordering = ['stock', 'price']

    def __str__(self):
        if self.order_type == self.BID:
            quantity = -1 * self.quantity
        else:
            quantity = self.quantity
        return "%s: %s@%s" % (self.stock, quantity, self.price)